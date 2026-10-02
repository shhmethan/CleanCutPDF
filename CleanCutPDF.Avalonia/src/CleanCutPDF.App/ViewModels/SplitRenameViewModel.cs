using System.ComponentModel;
using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Pdf;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>
/// Split &amp; Rename editor. Phase 1 shows the active document and its preview;
/// split detection, part cards, and workspace fields arrive in Phase 2.
/// </summary>
public sealed partial class SplitRenameViewModel : ObservableObject
{
    private readonly DocumentStore _store;
    private readonly NavigationService _navigation;

    public SplitRenameViewModel(DocumentStore store, NavigationService navigation,
        PagePreviewService previews, CrashLog crashLog)
    {
        _store = store;
        _navigation = navigation;
        Preview = new PdfPreviewViewModel(previews, crashLog);
        _store.PropertyChanged += OnStoreChanged;
    }

    public PdfPreviewViewModel Preview { get; }

    public DocumentItemViewModel? Document => _store.ActiveDocument;

    public bool HasDocument => Document is not null;

    [RelayCommand]
    private void CloseDocument()
    {
        if (Document is { } document)
        {
            _store.Close([document]);
        }
    }

    [RelayCommand]
    private void BackToInbox() => _navigation.NavigateTo(AppPage.Inbox);

    private void OnStoreChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName != nameof(DocumentStore.ActiveDocument))
        {
            return;
        }

        OnPropertyChanged(nameof(Document));
        OnPropertyChanged(nameof(HasDocument));
        CloseDocumentCommand.NotifyCanExecuteChanged();
        Preview.ShowDocument(Document);
    }
}
