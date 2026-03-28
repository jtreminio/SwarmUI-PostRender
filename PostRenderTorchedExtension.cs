using SwarmUI.Builtin_ComfyUIBackend;
using SwarmUI.Core;
using SwarmUI.Text2Image;
using SwarmUI.Utils;
using System.IO;

namespace PostRenderTorched;

public class PostRenderTorchedExtension : Extension
{
    public const string FeatureFlag = "feature_flag_post_render";
    public static T2IParamGroup PostRenderGroup;
    private readonly LensProfileFeature LensProfile = new();
    private readonly LensDistortionFeature LensDistortion = new();
    private readonly ChromaticAberrationFeature ChromaticAberration = new();
    private readonly DepthMapBlurFeature DepthMapBlur = new();
    private readonly RadialBlurFeature RadialBlur = new();
    private readonly FilmStockColorFeature FilmStockColor = new();
    private readonly LutFeature Lut = new();
    private readonly ColorWarperFeature ColorWarper = new();
    private readonly SkinToneUniformityFeature SkinToneUniformity = new();
    private readonly PrintStockFeature PrintStock = new();
    private readonly FilmStockBWFeature FilmStockBW = new();
    private readonly FilmGrainFeature FilmGrain = new();
    private readonly VignetteFeature Vignette = new();

    public override void OnInit()
    {
        Logs.Info("PostRender Torched Extension initializing...");

        var nodeFolder = Path.GetFullPath(Path.Join(FilePath, "comfy_node"));
        SharedOptionCatalogs.Initialize(FilePath);
        ComfyUISelfStartBackend.CustomNodePaths.Add(nodeFolder);
        Logs.Init($"PostRender Torched: added {nodeFolder} to ComfyUI CustomNodePaths");
        ComfyUIBackendExtension.FeaturesSupported.UnionWith([FeatureFlag]);
        ComfyUIBackendExtension.FeaturesDiscardIfNotFound.UnionWith([FeatureFlag]);

        PostRenderGroup = new(
            Name: "Post Render",
            Toggles: false,
            Open: false,
            IsAdvanced: false,
            OrderPriority: 9.1
        );

        int featurePriority = 1;
        LensProfile.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        LensDistortion.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        ChromaticAberration.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        DepthMapBlur.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        RadialBlur.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        FilmStockColor.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        Lut.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        ColorWarper.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        SkinToneUniformity.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        PrintStock.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        FilmStockBW.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        FilmGrain.RegisterFeature(PostRenderGroup, featurePriority);
        featurePriority += 1;
        Vignette.RegisterFeature(PostRenderGroup, featurePriority);

        double stepPriority = 9.90;
        WorkflowGenerator.AddStep(LensProfile.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(LensDistortion.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(ChromaticAberration.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(DepthMapBlur.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(RadialBlur.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(FilmStockColor.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(Lut.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(ColorWarper.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(SkinToneUniformity.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(PrintStock.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(FilmStockBW.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(FilmGrain.RegisterWorkflowStep, stepPriority);
        stepPriority += 0.005;
        WorkflowGenerator.AddStep(Vignette.RegisterWorkflowStep, stepPriority);
    }
}
