using CleanCutPDF.Core.Models;

namespace CleanCutPDF.Core.Pdf;

public readonly record struct PreviewKey(string Path, FileSignature Signature, int PageIndex, int Width);

/// <summary>
/// Thread-safe LRU cache of rendered pages bounded by total pixel bytes, so
/// paging back and forth (or returning to a document) is instant.
/// </summary>
public sealed class PagePreviewCache(long maxBytes = 192L * 1024 * 1024)
{
    private readonly object _gate = new();
    private readonly Dictionary<PreviewKey, LinkedListNode<(PreviewKey Key, RenderedPage Page)>> _map = new();
    private readonly LinkedList<(PreviewKey Key, RenderedPage Page)> _order = new();
    private long _bytes;

    public long MaxBytes { get; } = maxBytes;

    public long CurrentBytes
    {
        get { lock (_gate) return _bytes; }
    }

    public int Count
    {
        get { lock (_gate) return _map.Count; }
    }

    public bool TryGet(PreviewKey key, out RenderedPage page)
    {
        lock (_gate)
        {
            if (_map.TryGetValue(key, out var node))
            {
                _order.Remove(node);
                _order.AddFirst(node);
                page = node.Value.Page;
                return true;
            }
        }

        page = null!;
        return false;
    }

    public void Add(PreviewKey key, RenderedPage page)
    {
        if (page.ByteSize > MaxBytes)
        {
            return;
        }

        lock (_gate)
        {
            if (_map.Remove(key, out var existing))
            {
                _order.Remove(existing);
                _bytes -= existing.Value.Page.ByteSize;
            }

            _map[key] = _order.AddFirst((key, page));
            _bytes += page.ByteSize;

            while (_bytes > MaxBytes && _order.Last is { } last)
            {
                _order.RemoveLast();
                _map.Remove(last.Value.Key);
                _bytes -= last.Value.Page.ByteSize;
            }
        }
    }

    /// <summary>Drops every cached page for a document (e.g. when it is closed).</summary>
    public void Invalidate(string path)
    {
        lock (_gate)
        {
            foreach (var key in _map.Keys.Where(k => string.Equals(k.Path, path, StringComparison.OrdinalIgnoreCase)).ToList())
            {
                var node = _map[key];
                _order.Remove(node);
                _map.Remove(key);
                _bytes -= node.Value.Page.ByteSize;
            }
        }
    }
}
