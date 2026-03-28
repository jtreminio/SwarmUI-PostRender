using Newtonsoft.Json.Linq;
using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Text2Image;

namespace PostRenderTorched;

internal sealed class LensDistortionFeature
{
    public const string NodeName = "ProPostLensDistortion";
    private T2IRegisteredParam<string> Lens;
    private T2IRegisteredParam<float> Strength;
    private T2IRegisteredParam<float> K1;
    private T2IRegisteredParam<float> K2;

    public void RegisterFeature(T2IParamGroup group, int featurePriority)
    {
        ComfyUIBackendExtension.NodeToFeatureMap[NodeName] = PostRenderTorchedExtension.FeatureFlag;

        T2IParamGroup lensDistortionGroup = new(
            Name: "Lens Distortion",
            Toggles: true,
            Open: false,
            IsAdvanced: false,
            OrderPriority: featurePriority,
            Description: "Manual distortion control. Stacking this with Lens Profile is intentional and cumulative.",
            Parent: group
        );

        int orderPriority = 0;
        string defaultLens = SharedOptionCatalogs.GetLensDistortionLensDefault();

        Lens = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Lens Distortion Lens",
            Description: "Choose a preset lens profile or Custom to use the manual coefficients below.",
            Default: defaultLens,
            GetValues: _ => SharedOptionCatalogs.GetLensDistortionLenses(),
            Group: lensDistortionGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Strength = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Lens Distortion Strength",
            Description: "Scales the preset or manual distortion amount. Negative values invert the effect.",
            Default: "1.0",
            Min: -2.0, Max: 2.0, Step: 0.1,
            ViewType: ParamViewType.SLIDER,
            Group: lensDistortionGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        K1 = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Lens Distortion K One",
            Description: "Primary radial distortion coefficient (k1) used when Lens is set to Custom.",
            Default: "0.0",
            Min: -1.0, Max: 1.0, Step: 0.01,
            ViewType: ParamViewType.SLIDER,
            Group: lensDistortionGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        K2 = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Lens Distortion K Two",
            Description: "Secondary radial distortion coefficient (k2) used when Lens is set to Custom.",
            Default: "0.0",
            Min: -0.5, Max: 0.5, Step: 0.01,
            ViewType: ParamViewType.SLIDER,
            Group: lensDistortionGroup,
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
            ["strength"] = g.UserInput.Get(Strength),
            ["k1"] = g.UserInput.Get(K1),
            ["k2"] = g.UserInput.Get(K2),
        });
        g.CurrentMedia = g.CurrentMedia.WithPath([lensNode, 0]);
    }
}
