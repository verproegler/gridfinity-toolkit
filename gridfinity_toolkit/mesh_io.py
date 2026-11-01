"""Triangle meshes: STL/3MF reading and writing, welding and small helpers."""

import struct
import zipfile
from xml.sax.saxutils import escape

import numpy as np

STL_DIR = "STL"   # STL files go into this sub folder, 3MF files stay in the export folder

_STL_RECORD = np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")])


def load_stl(path):
    """Return an (n, 3, 3) array of triangles (binary and ASCII STL)."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + n * 50 == len(data):
            arr = np.frombuffer(data, dtype=_STL_RECORD, count=n, offset=84)
            return arr["v"].reshape(-1, 3, 3).astype(np.float64)
    verts = []
    for line in data.decode("ascii", errors="ignore").splitlines():
        parts = line.split()
        if parts and parts[0] == "vertex":
            verts.append([float(p) for p in parts[1:4]])
    if not verts or len(verts) % 3:
        raise ValueError(f"Not a valid STL file: {path}")
    return np.array(verts, dtype=np.float64).reshape(-1, 3, 3)


def save_stl(path, tris, name="gridfinity"):
    """Write triangles (n, 3, 3) as binary STL."""
    tris = np.asarray(tris, dtype=np.float32)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm = np.where(ln > 0, nrm / np.maximum(ln, 1e-12), 0).astype(np.float32)
    rec = np.zeros(len(tris), dtype=_STL_RECORD)
    rec["n"] = nrm
    rec["v"] = tris.reshape(-1, 9)
    with open(path, "wb") as f:
        f.write(name.encode("ascii", "ignore")[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        f.write(rec.tobytes())


def weld(tris, tol=1e-3):
    """Triangle soup -> (vertices, faces). Removes degenerate triangles."""
    key = np.round(tris.reshape(-1, 3) / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    verts = tris.reshape(-1, 3)[first]
    faces = inv.reshape(-1, 3)
    ok = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 2] != faces[:, 0])
    return verts, faces[ok]


def open_edges(tris):
    """Number of edges not shared by exactly two triangles (0 = watertight)."""
    _, f = weld(tris)
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return int((cnt != 2).sum())


def fix_t_junctions(tris, tol=1e-3, max_iter=10):
    """Close seams where one side has more points than the other by splitting open edges
    at the boundary points lying on them."""
    for _ in range(max_iter):
        v, f = weld(tris, tol)
        e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
        owner = np.tile(np.arange(len(f)), 3)
        slot = np.repeat([0, 1, 2], len(f))
        _, inv, cnt = np.unique(np.sort(e, axis=1), axis=0, return_inverse=True, return_counts=True)
        open_ = np.nonzero(cnt[inv] == 1)[0]
        if not len(open_):
            break
        bverts = np.unique(e[open_])
        bp = v[bverts]
        new_faces = {}
        for idx in open_:
            fi = owner[idx]
            if fi in new_faces:
                continue
            a, b = e[idx]
            pa, pb = v[a], v[b]
            d = pb - pa
            t = ((bp - pa) @ d) / (d @ d)
            dist = np.linalg.norm(bp - (pa + np.outer(t, d)), axis=1)
            hit = (t > 1e-6) & (t < 1 - 1e-6) & (dist < tol)
            if not hit.any():
                continue
            order = np.argsort(t[hit])
            pts = [a] + list(bverts[hit][order]) + [b]
            c = f[fi][(slot[idx] + 2) % 3]
            new_faces[fi] = [(pts[i], pts[i + 1], c) for i in range(len(pts) - 1)]
        if not new_faces:
            break
        keep = np.ones(len(f), bool)
        keep[list(new_faces)] = False
        add = np.array([tri for faces in new_faces.values() for tri in faces])
        tris = np.concatenate([v[f[keep]], v[add]])
    return tris


def box(sx, sy, sz):
    """Axis-aligned box from the origin as triangles (outward normals)."""
    p = np.array([[0, 0, 0], [sx, 0, 0], [sx, sy, 0], [0, sy, 0],
                  [0, 0, sz], [sx, 0, sz], [sx, sy, sz], [0, sy, sz]], dtype=np.float64)
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return p[np.array(f)]


def box_mesh(x, y, z, sx, sy, sz):
    """Box at (x, y, z) as (vertices, faces)."""
    tris = box(sx, sy, sz) + [x, y, z]
    return tris.reshape(-1, 3), np.arange(len(tris) * 3).reshape(-1, 3)


# ---------------------------------------------------------------------------
# 3MF
# ---------------------------------------------------------------------------

def mesh_xml(oid, name, v, f):
    """<object> element of a 3MF model."""
    out = [f'<object id="{oid}" name="{escape(str(name), {chr(34): "&quot;"})}" type="model"><mesh><vertices>']
    out.extend(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in v)
    out.append('</vertices><triangles>')
    out.extend(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
    out.append('</triangles></mesh></object>')
    return "\n".join(out)


def model_xml(objects, items, metadata=None, extra_ns=""):
    """3MF model document. objects: list of mesh_xml strings, items: [(object id, 12 transform values)]."""
    head = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<model unit="millimeter" xml:lang="en-US" '
            f'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"{extra_ns}>']
    for k, v in (metadata or {}).items():
        head.append(f'<metadata name="{k}">{escape(str(v))}</metadata>')
    body = ["<resources>"] + list(objects) + ["</resources><build>"]
    body += [f'<item objectid="{oid}" transform="{" ".join(f"{x:.4f}" for x in m)}" printable="1"/>'
             for oid, m in items]
    body.append("</build></model>")
    return "\n".join(head + body)


def write_3mf(path, model, extra_files=None):
    """Write a 3MF package with the given model document and optional extra files."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                   '<Default Extension="config" ContentType="text/xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                   'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
                   '</Relationships>')
        z.writestr("3D/3dmodel.model", model)
        for name, data in (extra_files or {}).items():
            z.writestr(name, data)


def save_3mf_objects(path, objects, items):
    """objects: {id: (name, triangles)}, items: [(id, 12 transform values)]."""
    xml = [mesh_xml(oid, name, *weld(tris)) for oid, (name, tris) in objects.items()]
    write_3mf(path, model_xml(xml, items))


def save_3mf_single(path, v, f, name, center=(128.0, 128.0)):
    """One mesh as 3MF, placed at 'center' on the bed."""
    write_3mf(path, model_xml([mesh_xml(1, name, v, f)],
                              [(1, [1, 0, 0, 0, 1, 0, 0, 0, 1, center[0], center[1], 0])]))


def save_stl_mesh(path, v, f, name="gridfinity"):
    save_stl(path, np.asarray(v)[np.asarray(f)], name)
