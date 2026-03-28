using Newtonsoft.Json.Linq;
using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Text2Image;

namespace PostRenderTorched;

internal sealed class SkinToneUniformityFeature
{
    public const string NodeName = "ProPostSkinToneUniformity";
    private T2IRegisteredParam<string> Preset;
    private T2IRegisteredParam<float> Amount;
    private T2IRegisteredParam<float> SmoothingRadius;
    private T2IRegisteredParam<float> HueCenter;
    private T2IRegisteredParam<float> HueWidth;
    private T2IRegisteredParam<float> SaturationMin;
    private T2IRegisteredParam<float> SaturationMax;
    private T2IRegisteredParam<float> LuminanceMin;
    private T2IRegisteredParam<float> LuminanceMax;
    private T2IRegisteredParam<float> Strength;

    public void RegisterFeature(T2IParamGroup group, int featurePriority)
    {
        ComfyUIBackendExtension.NodeToFeatureMap[NodeName] = PostRenderTorchedExtension.FeatureFlag;

        T2IParamGroup skinToneUniformityGroup = new(
            Name: "Skin Tone Uniformity",
            Toggles: true,
            Open: false,
            IsAdvanced: false,
            OrderPriority: featurePriority,
            Description: "Selective skin-tone cleanup and smoothing after the main global grade.",
            Parent: group
        );

        int orderPriority = 0;
        string defaultPreset = SharedOptionCatalogs.GetSkinTonePresetDefault();

        Preset = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Skin Tone Uniformity Preset",
            Description: "Preset skin-tone selection ranges. Choose Custom to use the manual ranges below.",
            Default: defaultPreset,
            GetValues: _ => SharedOptionCatalogs.GetSkinTonePresets(),
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Amount = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Amount",
            Description: "How strongly to pull skin tones toward the local average.",
            Default: "60.0",
            Min: 0.0, Max: 100.0, Step: 1.0,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        SmoothingRadius = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Smoothing Radius",
            Description: "Radius used when averaging nearby skin tones.",
            Default: "60.0",
            Min: 10.0, Max: 100.0, Step: 1.0,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        HueCenter = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Hue Center",
            Description: "Center hue of the detected skin-tone range.",
            Default: "25.0",
            Min: 0.0, Max: 360.0, Step: 1.0,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        HueWidth = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Hue Width",
            Description: "Hue range covered by the selected skin-tone detector.",
            Default: "45.0",
            Min: 10.0, Max: 90.0, Step: 1.0,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        SaturationMin = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Saturation Min",
            Description: "Minimum saturation included in the skin-tone detector.",
            Default: "0.08",
            Min: 0.0, Max: 0.5, Step: 0.01,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        SaturationMax = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Saturation Max",
            Description: "Maximum saturation included in the skin-tone detector.",
            Default: "0.85",
            Min: 0.3, Max: 1.0, Step: 0.01,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        LuminanceMin = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Luminance Min",
            Description: "Minimum luminance included in the skin-tone detector.",
            Default: "0.10",
            Min: 0.0, Max: 0.5, Step: 0.01,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        LuminanceMax = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Luminance Max",
            Description: "Maximum luminance included in the skin-tone detector.",
            Default: "0.92",
            Min: 0.5, Max: 1.0, Step: 0.01,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Strength = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Skin Tone Uniformity Strength",
            Description: "Blend strength for the skin-tone uniformity effect.",
            Default: "1.0",
            Min: 0.0, Max: 1.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: skinToneUniformityGroup,
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

        string skinToneUniformityNode = g.CreateNode(NodeName, new JObject
        {
            ["image"] = g.CurrentMedia.Path,
            ["preset"] = preset,
            ["amount"] = g.UserInput.Get(Amount),
            ["smoothing_radius"] = g.UserInput.Get(SmoothingRadius),
            ["hue_center"] = g.UserInput.Get(HueCenter),
            ["hue_width"] = g.UserInput.Get(HueWidth),
            ["saturation_min"] = g.UserInput.Get(SaturationMin),
            ["saturation_max"] = g.UserInput.Get(SaturationMax),
            ["luminance_min"] = g.UserInput.Get(LuminanceMin),
            ["luminance_max"] = g.UserInput.Get(LuminanceMax),
            ["strength"] = g.UserInput.Get(Strength),
        });
        // The node also emits a mask preview, but the image chain should continue from output 0.
        g.CurrentMedia = g.CurrentMedia.WithPath([skinToneUniformityNode, 0]);
    }
}
