using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

internal static class Program
{
    private static int Main(string[] args)
    {
        try
        {
            var options = CliOptions.Parse(args);
            if (!string.Equals(options.Adapter, "zcap-dotnet-reflection", StringComparison.Ordinal))
            {
                Console.Error.WriteLine($"Unsupported adapter: {options.Adapter}");
                return 2;
            }

            var assemblyPath = Path.GetFullPath(options.AssemblyPath);
            var fixturesDir = Path.GetFullPath(options.FixturesDir);
            var outputPath = Path.GetFullPath(options.OutputPath);

            var runner = new ZcapDotnetReflectionRunner(assemblyPath, fixturesDir);
            var fixtures = Directory.GetFiles(fixturesDir, "*.json", SearchOption.AllDirectories)
                .OrderBy(path => path, StringComparer.Ordinal)
                .ToArray();

            var entries = fixtures.Select(path => runner.ProcessFixture(path)).ToArray();
            var kindCounts = entries
                .GroupBy(entry => entry.Kind, StringComparer.Ordinal)
                .OrderBy(group => group.Key, StringComparer.Ordinal)
                .ToDictionary(group => group.Key, group => group.Count(), StringComparer.Ordinal);

            var manifest = new
            {
                manifest_version = 1,
                runner = "dotnet",
                adapter = options.Adapter,
                generated_at_utc = DateTimeOffset.UtcNow.ToString("O"),
                fixture_count = entries.Length,
                fixture_kind_counts = kindCounts,
                fixtures = entries
            };

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
            var json = JsonSerializer.Serialize(manifest, new JsonSerializerOptions
            {
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
                WriteIndented = true
            });
            File.WriteAllText(outputPath, json + Environment.NewLine, new UTF8Encoding(false));
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.ToString());
            return 1;
        }
    }
}

internal sealed record CliOptions(
    string Adapter,
    string AssemblyPath,
    string FixturesDir,
    string OutputPath)
{
    public static CliOptions Parse(string[] args)
    {
        string? adapter = null;
        string? assembly = null;
        string? fixtures = null;
        string? output = null;

        for (var i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--adapter":
                    adapter = args[++i];
                    break;
                case "--assembly":
                    assembly = args[++i];
                    break;
                case "--fixtures-dir":
                    fixtures = args[++i];
                    break;
                case "--output":
                    output = args[++i];
                    break;
                default:
                    throw new ArgumentException($"Unknown argument: {args[i]}");
            }
        }

        if (string.IsNullOrWhiteSpace(adapter)
            || string.IsNullOrWhiteSpace(assembly)
            || string.IsNullOrWhiteSpace(fixtures)
            || string.IsNullOrWhiteSpace(output))
        {
            throw new ArgumentException(
                "Required arguments: --adapter --assembly --fixtures-dir --output");
        }

        return new CliOptions(adapter!, assembly!, fixtures!, output!);
    }
}

internal sealed class FixtureManifestEntry
{
    [JsonPropertyName("name")]
    public required string Name { get; init; }

    [JsonPropertyName("kind")]
    public required string Kind { get; init; }

    [JsonPropertyName("tags")]
    public required string[] Tags { get; init; }

    [JsonPropertyName("status")]
    public required string Status { get; init; }

    [JsonPropertyName("fixture_path")]
    public required string FixturePath { get; init; }

    [JsonPropertyName("canonical_base64")]
    public string? CanonicalBase64 { get; init; }

    [JsonPropertyName("canonical_sha256")]
    public string? CanonicalSha256 { get; init; }

    [JsonPropertyName("canonical_utf8")]
    public string? CanonicalUtf8 { get; init; }

    [JsonPropertyName("error_type")]
    public string? ErrorType { get; init; }

    [JsonPropertyName("error")]
    public string? Error { get; init; }
}

internal sealed class ZcapDotnetReflectionRunner
{
    private readonly string _fixturesDir;
    private readonly Assembly _assembly;
    private readonly Type _capabilityType;
    private readonly Type _invocationType;
    private readonly Type _proofType;
    private readonly MethodInfo _canonicalizeCapabilityPayload;
    private readonly MethodInfo _canonicalizeInvocationPayload;

    public ZcapDotnetReflectionRunner(string assemblyPath, string fixturesDir)
    {
        if (!File.Exists(assemblyPath))
        {
            throw new FileNotFoundException("Assembly not found", assemblyPath);
        }

        _fixturesDir = Path.GetFullPath(fixturesDir);

        var assemblyDir = Path.GetDirectoryName(assemblyPath)!;
        AssemblyLoadContext.Default.Resolving += (_, assemblyName) =>
        {
            var candidate = Path.Combine(assemblyDir, $"{assemblyName.Name}.dll");
            return File.Exists(candidate) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(candidate) : null;
        };

        _assembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(assemblyPath);
        _capabilityType = RequireType("ZcapLd.Core.Models.Capability");
        _invocationType = RequireType("ZcapLd.Core.Models.Invocation");
        _proofType = RequireType("ZcapLd.Core.Models.Proof");

        var payloadBuilderType = RequireType("ZcapLd.Core.Cryptography.ProofSigningPayloadBuilder");
        _canonicalizeCapabilityPayload = RequireMethod(
            payloadBuilderType,
            "CanonicalizeCapabilityPayload");
        _canonicalizeInvocationPayload = RequireMethod(
            payloadBuilderType,
            "CanonicalizeInvocationPayload");
    }

    public FixtureManifestEntry ProcessFixture(string fixturePath)
    {
        using var fixtureDoc = JsonDocument.Parse(File.ReadAllText(fixturePath, Encoding.UTF8));
        var root = fixtureDoc.RootElement;
        var name = root.GetProperty("name").GetString()!;
        var kind = root.GetProperty("kind").GetString()!;
        var tags = root.GetProperty("tags").EnumerateArray()
            .Select(x => x.GetString()!)
            .ToArray();
        var relativeFixturePath = Path.GetRelativePath(_fixturesDir, fixturePath)
            .Replace(Path.DirectorySeparatorChar, '/');

        try
        {
            var documentJson = root.GetProperty("document").GetRawText();
            var proofJson = root.GetProperty("proof").GetRawText();
            var proof = Deserialize(proofJson, _proofType);

            byte[] canonical = kind switch
            {
                "capability" => InvokeCanonicalize(
                    _canonicalizeCapabilityPayload,
                    Deserialize(documentJson, _capabilityType),
                    proof),
                "invocation" => InvokeCanonicalize(
                    _canonicalizeInvocationPayload,
                    Deserialize(documentJson, _invocationType),
                    proof),
                _ => throw new InvalidOperationException($"Unknown fixture kind: {kind}")
            };

            return new FixtureManifestEntry
            {
                Name = name,
                Kind = kind,
                Tags = tags,
                Status = "ok",
                FixturePath = relativeFixturePath,
                CanonicalBase64 = Convert.ToBase64String(canonical),
                CanonicalSha256 = Convert.ToHexString(SHA256.HashData(canonical)).ToLowerInvariant(),
                CanonicalUtf8 = Encoding.UTF8.GetString(canonical)
            };
        }
        catch (TargetInvocationException ex) when (ex.InnerException is not null)
        {
            return ErrorEntry(name, kind, tags, relativeFixturePath, ex.InnerException);
        }
        catch (Exception ex)
        {
            return ErrorEntry(name, kind, tags, relativeFixturePath, ex);
        }
    }

    private static FixtureManifestEntry ErrorEntry(
        string name,
        string kind,
        string[] tags,
        string fixturePath,
        Exception ex)
    {
        return new FixtureManifestEntry
        {
            Name = name,
            Kind = kind,
            Tags = tags,
            Status = "error",
            FixturePath = fixturePath,
            ErrorType = ex.GetType().Name,
            Error = ex.Message
        };
    }

    private object Deserialize(string json, Type targetType)
    {
        var result = JsonSerializer.Deserialize(json, targetType, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = false
        });
        return result ?? throw new InvalidOperationException(
            $"Deserialization to {targetType.FullName} returned null.");
    }

    private Type RequireType(string fullName)
    {
        return _assembly.GetType(fullName, throwOnError: true)!;
    }

    private static byte[] InvokeCanonicalize(MethodInfo method, object document, object proof)
    {
        var parameterCount = method.GetParameters().Length;
        return parameterCount switch
        {
            2 => (byte[])method.Invoke(null, [document, proof])!,
            3 => (byte[])method.Invoke(null, [document, proof, null])!,
            _ => throw new InvalidOperationException(
                $"Unsupported canonicalize signature with {parameterCount} parameters.")
        };
    }

    private static MethodInfo RequireMethod(Type type, string name)
    {
        var method = type.GetMethods(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic)
            .Where(m => m.Name == name)
            .OrderByDescending(m => m.GetParameters().Length)
            .FirstOrDefault();
        return method ?? throw new MissingMethodException(type.FullName, name);
    }
}
