namespace CleanCutPDF.Core.Models;

/// <summary>Cheap facts about one page, gathered in a single trip to the PDF thread.</summary>
public sealed record PageAnalysis(int PageIndex, string Text, int AnnotationCount, float WidthPoints, float HeightPoints);
