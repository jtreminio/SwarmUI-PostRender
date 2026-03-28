using Newtonsoft.Json.Linq;
using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Text2Image;

namespace PostRenderTorched;

internal sealed class ColorWarperFeature
{
    public const string NodeName = "ProPostColorWarper";
    private T2IRegisteredParam<string> Preset;
    private T2IRegisteredParam<float> SourceHue;
    private T2IRegisteredParam<float> SourceHueWidth;
    private T2IRegisteredParam<float> SourceSatMin;
    private T2IRegisteredParam<float> SourceSatMax;
    private T2IRegisteredParam<float> HueShift;
    private T2IRegisteredParam<float> SatShift;
    private T2IRegisteredParam<float> Feather;
    private T2IRegisteredParam<float> Strength;

    public void RegisterFeature(T2IParamGroup group, int featurePriority)
    {
        ComfyUIBackendExtension.NodeToFeatureMap[NodeName] = PostRenderTorchedExtension.FeatureFlag;

        T2IParamGroup colorWarperGroup = new(
            Name: "Color Warper",
            Toggles: true,
            Open: false,
            IsAdvanced: false,
            OrderPriority: featurePriority,
            Description: "Selective hue and saturation remapping after the global look stage.",
            Parent: group
        );

        int orderPriority = 0;
        string defaultPreset = SharedOptionCatalogs.GetColorWarperPresetDefault();

        Preset = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Color Warper Preset",
            Description: "Preset region mapping for common grading moves. Use Custom (manual) to work entirely from the controls below.",
            Default: defaultPreset,
            GetValues: _ => SharedOptionCatalogs.GetColorWarperPresets(),
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        SourceHue = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Color Warper Source Hue",
            Description: "Center hue of the color region to target.",
            Default: "0.0",
            Min: 0.0, Max: 360.0, Step: 1.0,
            ViewType: ParamViewType.SLIDER,
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        SourceHueWidth = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Color Warper Source Hue Width",
            Description: "Hue range covered by the selected source region.",
            Default: "60.0",
            Min: 10.0, Max: 180.0, Step: 1.0,
            ViewType: ParamViewType.SLIDER,
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        SourceSatMin = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Color Warper Source Saturation Min",
            Description: "Minimum saturation included in the selected source region.",
            Default: "0.0",
            Min: 0.0, Max: 1.0, Step: 0.01,
            ViewType: ParamViewType.SLIDER,
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        SourceSatMax = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Color Warper Source Saturation Max",
            Description: "Maximum saturation included in the selected source region.",
            Default: "1.0",
            Min: 0.0, Max: 1.0, Step: 0.01,
            ViewType: ParamViewType.SLIDER,
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        HueShift = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Color Warper Hue Shift",
            Description: "How far to rotate the targeted hue range.",
            Default: "0.0",
            Min: -180.0, Max: 180.0, Step: 1.0,
            ViewType: ParamViewType.SLIDER,
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        SatShift = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Color Warper Saturation Shift",
            Description: "Relative saturation change for the targeted hue range.",
            Default: "0.0",
            Min: -100.0, Max: 100.0, Step: 1.0,
            ViewType: ParamViewType.SLIDER,
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Feather = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Color Warper Feather",
            Description: "Softness of the transition around the selected hue and saturation ranges.",
            Default: "0.5",
            Min: 0.1, Max: 1.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Strength = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Color Warper Strength",
            Description: "Blend strength for the color warper effect.",
            Default: "1.0",
            Min: 0.0, Max: 1.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: colorWarperGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));
    }

    public void RegisterWorkflowStep(WorkflowGenerator g)
    {
        if (!g.UserInput.TryGet(Preset, out string preset))
        {
            return;
        }

        string colorWarperNode = g.CreateNode(NodeName, new JObject
        {
            ["image"] = g.CurrentMedia.Path,
            ["preset"] = preset,
            ["source_hue"] = g.UserInput.Get(SourceHue),
            ["source_hue_width"] = g.UserInput.Get(SourceHueWidth),
            ["source_sat_min"] = g.UserInput.Get(SourceSatMin),
            ["source_sat_max"] = g.UserInput.Get(SourceSatMax),
            ["hue_shift"] = g.UserInput.Get(HueShift),
            ["sat_shift"] = g.UserInput.Get(SatShift),
            ["feather"] = g.UserInput.Get(Feather),
            ["strength"] = g.UserInput.Get(Strength),
        });
        g.CurrentMedia = g.CurrentMedia.WithPath([colorWarperNode, 0]);
    }
}
