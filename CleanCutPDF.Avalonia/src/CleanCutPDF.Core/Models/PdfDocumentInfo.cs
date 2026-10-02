namespace CleanCutPDF.Core.Models;

/// <summary>Lightweight metadata gathered when a PDF is imported.</summary>
public sealed record PdfDocumentInfo(string Path, int PageCount, FileSignature Signature);
