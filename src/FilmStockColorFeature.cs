using Newtonsoft.Json.Linq;
using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Text2Image;

namespace PostRenderTorched;

internal sealed class FilmStockColorFeature
{
    public const string NodeName = "ProPostFilmStockColor";
    private T2IRegisteredParam<string> FilmStock;
    private T2IRegisteredParam<float> Strength;
    private T2IRegisteredParam<float> OverrideToe;
    private T2IRegisteredParam<float> OverrideShoulder;
    private T2IRegisteredParam<float> OverrideGamma;

    public void RegisterFeature(T2IParamGroup group, int featurePriority)
    {
        ComfyUIBackendExtension.NodeToFeatureMap[NodeName] = PostRenderTorchedExtension.FeatureFlag;

        T2IParamGroup filmStockColorGroup = new(
            Name: "Film Stock (Color)",
            Toggles: true,
            Open: false,
            IsAdvanced: false,
            OrderPriority: featurePriority,
            Description: "Base analog color-character stage before LUT, selective grading, and print finishing.",
            Parent: group
        );

        int orderPriority = 0;
        string defaultFilmStock = SharedOptionCatalogs.GetColorFilmStockDefault();

        FilmStock = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Film Stock Color Stock",
            Description: "Color film stock profile used for the base analog look.",
            Default: defaultFilmStock,
            GetValues: _ => SharedOptionCatalogs.GetColorFilmStocks(),
            Group: filmStockColorGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Strength = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Film Stock Color Strength",
            Description: "Blend strength for the color film stock effect.",
            Default: "1.0",
            Min: 0.0, Max: 1.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: filmStockColorGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        OverrideToe = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Film Stock Color Override Toe",
            Description: "Override the stock toe value. Set to -1 to keep the stock default.",
            Default: "-1.0",
            Min: -1.0, Max: 5.0, Step: 0.1,
            ViewType: ParamViewType.SLIDER,
            Group: filmStockColorGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        OverrideShoulder = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Film Stock Color Override Shoulder",
            Description: "Override the stock shoulder value. Set to -1 to keep the stock default.",
            Default: "-1.0",
            Min: -1.0, Max: 5.0, Step: 0.1,
            ViewType: ParamViewType.SLIDER,
            Group: filmStockColorGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        OverrideGamma = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Film Stock Color Override Gamma",
            Description: "Override the stock gamma/slope value. Set to -1 to keep the stock default.",
            Default: "-1.0",
            Min: -1.0, Max: 3.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: filmStockColorGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));
    }

    public void RegisterWorkflowStep(WorkflowGenerator g)
    {
        if (!g.UserInput.TryGet(FilmStock, out string filmStock))
        {
            return;
        }

        string filmStockNode = g.CreateNode(NodeName, new JObject
        {
            ["image"] = g.CurrentMedia.Path,
            ["film_stock"] = filmStock,
            ["strength"] = g.UserInput.Get(Strength),
            ["override_toe"] = g.UserInput.Get(OverrideToe),
            ["override_shoulder"] = g.UserInput.Get(OverrideShoulder),
            ["override_gamma"] = g.UserInput.Get(OverrideGamma),
        });
        g.CurrentMedia = g.CurrentMedia.WithPath([filmStockNode, 0]);
    }
}
