using Newtonsoft.Json.Linq;
using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Text2Image;

namespace PostRenderTorched;

internal sealed class FilmStockBWFeature
{
    public const string NodeName = "ProPostFilmStockBW";
    private T2IRegisteredParam<string> FilmStock;
    private T2IRegisteredParam<string> ColorFilter;
    private T2IRegisteredParam<float> Strength;
    private T2IRegisteredParam<float> Contrast;
    private T2IRegisteredParam<float> ExposureShift;

    public void RegisterFeature(T2IParamGroup group, int featurePriority)
    {
        ComfyUIBackendExtension.NodeToFeatureMap[NodeName] = PostRenderTorchedExtension.FeatureFlag;

        T2IParamGroup filmStockBwGroup = new(
            Name: "Film Stock (B&W)",
            Toggles: true,
            Open: false,
            IsAdvanced: false,
            OrderPriority: featurePriority,
            Description: "Late monochrome finish placed after the color pipeline so later nodes do not reintroduce color.",
            Parent: group
        );

        int orderPriority = 0;
        string defaultFilmStock = SharedOptionCatalogs.GetBWFilmStockDefault();
        string defaultColorFilter = SharedOptionCatalogs.GetColorFilterDefault();

        FilmStock = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Film Stock BW Stock",
            Description: "Black-and-white film stock profile used for the final monochrome conversion.",
            Default: defaultFilmStock,
            GetValues: _ => SharedOptionCatalogs.GetBWFilmStocks(),
            Group: filmStockBwGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        ColorFilter = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Film Stock BW Color Filter",
            Description: "Simulated lens color filter applied during the monochrome conversion.",
            Default: defaultColorFilter,
            GetValues: _ => SharedOptionCatalogs.GetColorFilters(),
            Group: filmStockBwGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Strength = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Film Stock BW Strength",
            Description: "Blend strength for the black-and-white film stock effect.",
            Default: "1.0",
            Min: 0.0, Max: 1.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: filmStockBwGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Contrast = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Film Stock BW Contrast",
            Description: "Contrast trim applied on top of the selected black-and-white stock curve.",
            Default: "0.0",
            Min: -1.0, Max: 1.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: filmStockBwGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        ExposureShift = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Film Stock BW Exposure Shift",
            Description: "Exposure compensation applied before the stock curve.",
            Default: "0.0",
            Min: -3.0, Max: 3.0, Step: 0.25,
            ViewType: ParamViewType.SLIDER,
            Group: filmStockBwGroup,
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

        string filmStockBwNode = g.CreateNode(NodeName, new JObject
        {
            ["image"] = g.CurrentMedia.Path,
            ["film_stock"] = filmStock,
            ["color_filter"] = g.UserInput.Get(ColorFilter),
            ["strength"] = g.UserInput.Get(Strength),
            ["contrast"] = g.UserInput.Get(Contrast),
            ["exposure_shift"] = g.UserInput.Get(ExposureShift),
        });
        g.CurrentMedia = g.CurrentMedia.WithPath([filmStockBwNode, 0]);
    }
}
