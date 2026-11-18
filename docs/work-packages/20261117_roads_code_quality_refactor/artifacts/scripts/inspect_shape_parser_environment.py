"""Read-only parser availability and relevant source identity inspection."""
from pathlib import Path
import hashlib,json,os,sys
from wepppy.microservices.shape_converter import convert
from wepppy.microservices.shape_converter.parser_provenance import validate_parser_executable
root=Path('/workdir/wepppy');paths=[convert._SOURCE_PARSER_CLI,convert._INSTALLED_PARSER_CLI,convert._parser_cli_path()]
artifacts={}
for p in paths:
 for path in [p,Path(str(p)+'.json')]:artifacts[str(path)]={'exists':path.exists(),'file':path.is_file(),'executable':os.access(path,os.X_OK),'symlink':path.is_symlink()}
source_paths=sorted((root/'wepppy/microservices/shape_converter').glob('*.py'))+[root/'tests/shape_converter/integration/test_abuse_controls_api.py',root/'tests/shape_converter/helpers/archive_builder.py']
receipt={'label':sys.argv[1],'configured_parser_cli':os.environ.get('SHAPE_CONVERTER_PARSER_CLI'),'configured_scratch_root':os.environ.get('SHAPE_CONVERTER_SCRATCH_ROOT'),'selected_parser_cli':str(convert._parser_cli_path()),'validation':validate_parser_executable(convert._parser_cli_path()),'paths':artifacts,'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}}
p=Path('/tmp/roads-refactor-validation')/('shape-parser-environment-'+sys.argv[1]+'.json');p.write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='source_sha256'},indent=2))
