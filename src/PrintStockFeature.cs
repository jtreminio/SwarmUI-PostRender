using Newtonsoft.Json.Linq;
using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Text2Image;

namespace PostRenderTorched;

internal sealed class PrintStockFeature
{
    public const string NodeName = "ProPostPrintStock";
    private T2IRegisteredParam<string> PrintStock;
    private T2IRegisteredParam<float> Strength;
    private T2IRegisteredParam<float> ContrastBoost;

    public void RegisterFeature(T2IParamGroup group, int featurePriority)
    {
        ComfyUIBackendExtension.NodeToFeatureMap[NodeName] = PostRenderTorchedExtension.FeatureFlag;

        T2IParamGroup printStockGroup = new(
            Name: "Print Stock",
            Toggles: true,
            Open: false,
            IsAdvanced: false,
            OrderPriority: featurePriority,
            Description: "Late print and mastering stage after LUT and selective color adjustments.",
            Parent: group
        );

        int orderPriority = 0;
        string defaultPrintStock = SharedOptionCatalogs.GetPrintStockDefault();

        PrintStock = T2IParamTypes.Register<string>(new T2IParamType(
            Name: "Print Stock Profile",
            Description: "Print stock profile used for the late print/mastering look.",
            Default: defaultPrintStock,
            GetValues: _ => SharedOptionCatalogs.GetPrintStocks(),
            Group: printStockGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        Strength = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Print Stock Strength",
            Description: "Blend strength for the print stock effect.",
            Default: "1.0",
            Min: 0.0, Max: 1.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: printStockGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));

        ContrastBoost = T2IParamTypes.Register<float>(new T2IParamType(
            Name: "Print Stock Contrast Boost",
            Description: "Optional extra contrast added on top of the print stock curve.",
            Default: "0.0",
            Min: 0.0, Max: 1.0, Step: 0.05,
            ViewType: ParamViewType.SLIDER,
            Group: printStockGroup,
            FeatureFlag: PostRenderTorchedExtension.FeatureFlag,
            OrderPriority: orderPriority++
        ));
    }

    public void RegisterWorkflowStep(WorkflowGenerator g)
    {
        if (!g.UserInput.TryGet(PrintStock, out string printStock))
        {
            return;
        }

        string printStockNode = g.CreateNode(NodeName, new JObject
        {
            ["image"] = g.CurrentMedia.Path,
            ["print_stock"] = printStock,
            ["strength"] = g.UserInput.Get(Strength),
            ["contrast_boost"] = g.UserInput.Get(ContrastBoost),
        });
        g.CurrentMedia = g.CurrentMedia.WithPath([printStockNode, 0]);
    }
}
