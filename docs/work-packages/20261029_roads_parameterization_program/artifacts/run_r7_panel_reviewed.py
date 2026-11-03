"""Verify additive pre-execution review/scoring bindings, then run frozen panel."""
from pathlib import Path
import rebaseline_r7_panel as panel


def main():
    receipt_path=panel.ROOT/'execution-review.json'
    receipt=panel.seeds.read(receipt_path)
    assert receipt['panel_declaration_sha256']==panel.seeds.sha(panel.ROOT/'declaration.json')
    assert receipt['implementation_review_pass'] and receipt['scientific_review_pass']
    assert receipt['launcher_sha256']==panel.seeds.sha(__file__)
    for path,digest in receipt['files'].items():
        assert panel.seeds.sha(Path(path))==digest,path
    verified=panel.ROOT/'execution-review-verified.json'
    assert not verified.exists()
    panel.seeds.save(verified,dict(review_receipt_sha256=panel.seeds.sha(receipt_path)))
    panel.run()


if __name__=='__main__':
    main()
