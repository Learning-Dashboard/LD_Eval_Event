import os
from collections import defaultdict


def scan_quality_model_folder(root_dir, subfolder, props_loader, build_def):
    """
    Scanner for quality-model directories.

    Walks each subfolder under root_dir, looks in subfolder for .properties files,
    loads properties via props_loader, constructs definitions via build_def,
    and indexes them by quality_model and triggering events.
    """
    # Initialize dictionaries to hold definitions and event mappings
    all_by_qm, evt_by_qm = {}, {}

    # Iterate over each quality model folder
    for qm in os.listdir(root_dir):
        qm_path = os.path.join(root_dir, qm)
        if not os.path.isdir(qm_path):
            continue  # Skip if not a directory

        # Look for the specified subfolder (e.g., "metrics", "factors", "indicators")
        folder = os.path.join(qm_path, subfolder)  # p.ej.  QUALITY_MODELS/AWS/metrics
        if not os.path.isdir(folder):
            continue

        defs, evt_map = [], defaultdict(list)

        # Walk through all .properties files in subfolder tree
        for dirpath, _, files in os.walk(folder):
            for fname in [
                f for f in files if f.endswith(".properties")
            ]:  # Only .properties files
                fpath = os.path.join(dirpath, fname)
                props = props_loader(
                    fpath
                )  # Load properties using the provided loader function
                dfn = build_def(props, qm.lower(), fpath)
                defs.append(dfn)
                # Index by each relatedEvent
                for evt in props.get("relatedEvent", "").split(","):
                    evt = evt.strip()
                    if evt:
                        evt_map[evt].append(dfn)
        # Store everything per-quality-model lists and event maps
        all_by_qm[qm.lower()] = defs
        evt_by_qm[qm.lower()] = dict(evt_map)

    return all_by_qm, evt_by_qm
