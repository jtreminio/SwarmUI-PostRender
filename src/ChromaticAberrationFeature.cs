using Newtonsoft.Json.Linq;
using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Text2Image;

namespace PostRenderTorched;

internal sealed class ChromaticAberrationFeature
{
    public const string NodeName = "ProPostChromaticAberration";
    private T2IRegisteredParam<string> Lens;
    private T2IRegisteredParam<float> Strength;
    private T2IRegisteredParam<float> ShiftR;
    private T2IRegisteredParam<float> ShiftB;

    public void RegisterFeature(T2IParamGroup group, int featurePriority)
    {
        ComfyUIBackendExtension.NodeToFeatureMap[NodeName] = PostRenderTorchedExtension.FeatureFlag;

        T2IParamGroup chromaticAberrationGroup = new(
            Name: "Chromatic Aberration",
            Toggles: true,
            Open: false,
            IsAdvanced: false,
            OrderPriority: featurePriority,
            Description: "Manual lateral chromatic aberration control. Stacking this with Lens Profile is intentional and cumulative.",
            Parent: group
        );

        int orderPriority = 0;
        string defaultLens = SharedOptionCatalogs.GetChromaticAberrationLensDefault();

        Lens = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Chromatic Aberration Lens",
            Description: "Choose a preset lens profile or Custom to use the manual channel shifts below.",
            Default: defaultLens,
            GetValues: _ => SharedOptionCatalogs.GetChromaticAberrationLenses(),
            Group: chromaticAberrationGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Strength = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Chromatic Aberration Strength",
            Description: "Scales the preset or manual chromatic aberration amount.",
            Default: "1.0",
            Min: 0.0, Max: 3.0, Step: 0.1,
            ViewType: ParamViewType.SLIDER,
            Group: chromaticAberrationGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        ShiftR = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Chromatic Aberration Shift R",
            Description: "Red-channel edge shift used when Lens is set to Custom.",
            Default: "-1.0",
            Min: -5.0, Max: 5.0, Step: 0.1,
            ViewType: ParamViewType.SLIDER,
            Group: chromaticAberrationGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        ShiftB = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Chromatic Aberration Shift B",
            Description: "Blue-channel edge shift used when Lens is set to Custom.",
            Default: "1.0",
            Min: -5.0, Max: 5.0, Step: 0.1,
            ViewType: ParamViewType.SLIDER,
            Group: chromaticAberrationGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));
    }

    public void RegisterWorkflowStep(WorkflowGenerator g)
    {
        if (!g.UserInput.TryGet(Lens, out string lens))
        {
            return;
        }

        string chromaticAberrationNode = g.CreateNode(NodeName, new JObject
        {
            ["image"] = g.CurrentMedia.Path,
            ["lens"] = lens,
            ["strength"] = g.UserInput.Get(Strength),
            ["shift_r"] = g.UserInput.Get(ShiftR),
            ["shift_b"] = g.UserInput.Get(ShiftB),
        });
        g.CurrentMedia = g.CurrentMedia.WithPath([chromaticAberrationNode, 0]);
    }
}
