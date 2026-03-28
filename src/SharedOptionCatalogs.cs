using Newtonsoft.Json.Linq;
using SwarmUI.Utils;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace PostRenderTorched;

internal static class SharedOptionCatalogs
{
    private const string DataFolder = "comfy_node/ProPostTorched/data";
    private const string DefaultLensProfile = "ARRI/Zeiss Master Anamorphic 50mm T1.9";
    private const string DefaultLensProfileMode = "Add Aberrations";
    private const string DefaultLensCustom = "Custom";
    private const string DefaultColorFilmStock = "Neg / Kodak Portra 400";
    private const string DefaultBWFilmStock = "Ilford HP5 Plus 400";
    private const string DefaultColorFilter = "None";
    private const string DefaultPrintStock = "Kodak 2383";
    private const string DefaultColorWarperPreset = "Custom (manual)";
    private const string DefaultSkinTonePreset = "Universal - all skin tones";

    private static readonly object CatalogLock = new();
    private static string ExtensionRoot;
    private static JObject FilmCatalog;
    private static JObject PrintCatalog;
    private static JObject LensCatalog;
    private static JObject GradingCatalog;

    public static void Initialize(string extensionRoot)
    {
        lock (CatalogLock)
        {
            ExtensionRoot = extensionRoot;
            FilmCatalog = null;
            PrintCatalog = null;
            LensCatalog = null;
            GradingCatalog = null;
        }
    }

    public static List<string> GetColorFilmStocks()
    {
        return ReadStringList(GetFilmCatalog(), "color_film_stocks", DefaultColorFilmStock);
    }

    public static string GetColorFilmStockDefault()
    {
        return ReadDefault(GetFilmCatalog(), "film_stock_color", DefaultColorFilmStock, GetColorFilmStocks());
    }

    public static List<string> GetBWFilmStocks()
    {
        return ReadStringList(GetFilmCatalog(), "bw_film_stocks", DefaultBWFilmStock);
    }

    public static string GetBWFilmStockDefault()
    {
        return ReadDefault(GetFilmCatalog(), "film_stock_bw", DefaultBWFilmStock, GetBWFilmStocks());
    }

    public static List<string> GetColorFilters()
    {
        return ReadStringList(GetFilmCatalog(), "color_filters", DefaultColorFilter);
    }

    public static string GetColorFilterDefault()
    {
        return ReadDefault(GetFilmCatalog(), "film_stock_bw_color_filter", DefaultColorFilter, GetColorFilters());
    }

    public static List<string> GetPrintStocks()
    {
        return ReadStringList(GetPrintCatalog(), "print_stocks", DefaultPrintStock);
    }

    public static string GetPrintStockDefault()
    {
        return ReadDefault(GetPrintCatalog(), "print_stock", DefaultPrintStock, GetPrintStocks());
    }

    public static List<string> GetLensProfiles()
    {
        return ReadStringList(GetLensCatalog(), "lens_profiles", DefaultLensProfile);
    }

    public static string GetLensProfileDefault()
    {
        return ReadDefault(GetLensCatalog(), "lens_profile_lens", DefaultLensProfile, GetLensProfiles());
    }

    public static List<string> GetLensProfileModes()
    {
        return ReadStringList(GetLensCatalog(), "lens_profile_modes", DefaultLensProfileMode, "Correct Aberrations");
    }

    public static string GetLensProfileModeDefault()
    {
        return ReadDefault(GetLensCatalog(), "lens_profile_mode", DefaultLensProfileMode, GetLensProfileModes());
    }

    public static List<string> GetLensDistortionLenses()
    {
        List<string> lensOptions = PrependUnique(DefaultLensCustom, GetLensProfiles());
        string defaultLens = ReadDefault(GetLensCatalog(), "lens_distortion_lens", DefaultLensCustom, lensOptions);
        return PrependUnique(defaultLens, GetLensProfiles());
    }

    public static string GetLensDistortionLensDefault()
    {
        return ReadDefault(GetLensCatalog(), "lens_distortion_lens", DefaultLensCustom, GetLensDistortionLenses());
    }

    public static List<string> GetChromaticAberrationLenses()
    {
        List<string> lensOptions = PrependUnique(DefaultLensCustom, GetLensProfiles());
        string defaultLens = ReadDefault(GetLensCatalog(), "chromatic_aberration_lens", DefaultLensCustom, lensOptions);
        return PrependUnique(defaultLens, GetLensProfiles());
    }

    public static string GetChromaticAberrationLensDefault()
    {
        return ReadDefault(GetLensCatalog(), "chromatic_aberration_lens", DefaultLensCustom, GetChromaticAberrationLenses());
    }

    public static List<string> GetColorWarperPresets()
    {
        return ReadStringList(GetGradingCatalog(), "color_warper_presets", DefaultColorWarperPreset);
    }

    public static string GetColorWarperPresetDefault()
    {
        return ReadDefault(GetGradingCatalog(), "color_warper_preset", DefaultColorWarperPreset, GetColorWarperPresets());
    }

    public static List<string> GetSkinTonePresets()
    {
        return ReadStringList(GetGradingCatalog(), "skin_tone_presets", DefaultSkinTonePreset, "Custom");
    }

    public static string GetSkinTonePresetDefault()
    {
        return ReadDefault(GetGradingCatalog(), "skin_tone_preset", DefaultSkinTonePreset, GetSkinTonePresets());
    }

    private static JObject GetFilmCatalog()
    {
        return GetCatalog(ref FilmCatalog, "film_options.json");
    }

    private static JObject GetPrintCatalog()
    {
        return GetCatalog(ref PrintCatalog, "print_options.json");
    }

    private static JObject GetLensCatalog()
    {
        return GetCatalog(ref LensCatalog, "lens_options.json");
    }

    private static JObject GetGradingCatalog()
    {
        return GetCatalog(ref GradingCatalog, "grading_options.json");
    }

    private static JObject GetCatalog(ref JObject cache, string fileName)
    {
        lock (CatalogLock)
        {
            if (cache is not null)
            {
                return cache;
            }

            if (string.IsNullOrWhiteSpace(ExtensionRoot))
            {
                cache = new JObject();
                return cache;
            }

            string catalogPath = Path.GetFullPath(Path.Join(ExtensionRoot, DataFolder, fileName));
            try
            {
                if (!File.Exists(catalogPath))
                {
                    Logs.Warning($"PostRender Torched: shared option catalog '{catalogPath}' not found, using fallback values.");
                    cache = new JObject();
                    return cache;
                }

                cache = JObject.Parse(File.ReadAllText(catalogPath));
            }
            catch (Exception ex)
            {
                Logs.Warning($"PostRender Torched: failed to read shared option catalog '{catalogPath}': {ex.Message}");
                cache = new JObject();
            }

            return cache;
        }
    }

    private static List<string> ReadStringList(JObject catalog, string key, params string[] fallbackValues)
    {
        if (catalog[key] is JArray array)
        {
            List<string> values = [.. array.Values<string>().Where(value => !string.IsNullOrWhiteSpace(value))];
            if (values.Count > 0)
            {
                return values;
            }
        }

        return [.. fallbackValues.Where(value => !string.IsNullOrWhiteSpace(value))];
    }

    private static string ReadDefault(JObject catalog, string key, string fallbackValue)
    {
        string value = catalog["defaults"]?[key]?.Value<string>();
        return string.IsNullOrWhiteSpace(value) ? fallbackValue : value;
    }

    private static string ReadDefault(JObject catalog, string key, string fallbackValue, List<string> validValues)
    {
        string value = ReadDefault(catalog, key, fallbackValue);
        if (validValues.Count == 0 || validValues.Contains(value))
        {
            return value;
        }

        return validValues.Contains(fallbackValue) ? fallbackValue : validValues[0];
    }

    private static List<string> PrependUnique(string firstValue, List<string> values)
    {
        List<string> merged = [];
        if (!string.IsNullOrWhiteSpace(firstValue))
        {
            merged.Add(firstValue);
        }

        foreach (string value in values)
        {
            if (!string.IsNullOrWhiteSpace(value) && !merged.Contains(value))
            {
                merged.Add(value);
            }
        }

        return merged;
    }
}
