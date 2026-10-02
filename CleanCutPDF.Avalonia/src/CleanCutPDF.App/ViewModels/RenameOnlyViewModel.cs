using CommunityToolkit.Mvvm.ComponentModel;

namespace CleanCutPDF.App.ViewModels;

/// <summary>Rename Only mode. Placeholder until Phase 3.</summary>
public sealed class RenameOnlyViewModel : ObservableObject
{
    public IReadOnlyList<string> PlannedFeatures { get; } =
    [
        "Add one or more PDFs; each PDF is treated as one complete document (no SPLIT HERE markers)",
        "File list with remove (✕) and Clear",
        "Uses the normal workspace fields and filename template",
        "Create renamed copies in an output folder, or rename originals in place (with confirmation)",
        "Unique filenames (_2, _3, …) so nothing is overwritten"
    ];
}
