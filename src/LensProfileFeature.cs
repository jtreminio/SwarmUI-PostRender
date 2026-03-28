using Newtonsoft.Json.Linq;
using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Text2Image;

namespace PostRenderTorched;

internal sealed class LensProfileFeature
{
    public const string NodeName = "ProPostLensProfile";
    private T2IRegisteredParam<string> Lens;
    private T2IRegisteredParam<string> Mode;
    private T2IRegisteredParam<float> Strength;

    public void RegisterFeature(T2IParamGroup group, int featurePriority)
    {
        ComfyUIBackendExtension.NodeToFeatureMap[NodeName] = PostRenderTorchedExtension.FeatureFlag;

        T2IParamGroup lensProfileGroup = new(
            Name: "Lens Profile",
            Toggles: true,
            Open: false,
            IsAdvanced: false,
            OrderPriority: featurePriority,
            Description: "Preset lens-character stage. This overlaps intentionally with Lens Distortion and Chromatic Aberration, so stacking them is cumulative.",
            Parent: group
        );

        int orderPriority = 0;
        string defaultLens = SharedOptionCatalogs.GetLensProfileDefault();
        string defaultMode = SharedOptionCatalogs.GetLensProfileModeDefault();

        Lens = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Lens Profile Lens",
            Description: "Preset lens profile used to add or correct distortion, vignette, and chromatic aberration.",
            Default: defaultLens,
            GetValues: _ => SharedOptionCatalogs.GetLensProfiles(),
            Group: lensProfileGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Mode = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Lens Profile Mode",
            Description: "Choose whether to emulate the lens character or correct it.",
            Default: defaultMode,
            GetValues: _ => SharedOptionCatalogs.GetLensProfileModes(),
            Group: lensProfileGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Strength = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Lens Profile Strength",
            Description: "Overall intensity of the lens profile effect.",
            Default: "1.0",
            Min: 0.0, Max: 2.0, Step: 0.1,
            ViewType: ParamViewType.SLIDER,
            Group: lensProfileGroup,
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

        string lensNode = g.CreateNode(NodeName, new JObject
        {
            ["image"] = g.CurrentMedia.Path,
            ["lens"] = lens,
            ["mode"] = g.UserInput.Get(Mode),
            ["strength"] = g.UserInput.Get(Strength),
        });
        g.CurrentMedia = g.CurrentMedia.WithPath([lensNode, 0]);
    }
}
