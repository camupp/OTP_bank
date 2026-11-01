// Current self-read deck builder: 8 main slides and 19 readable appendices.
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const here=path.dirname(fileURLToPath(import.meta.url));
const result=spawnSync(process.env.OTP_PRESENTATION_PYTHON || '/opt/homebrew/bin/python3.12', [path.join(here,'build_read_deck.py')], {stdio:'inherit',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
if(result.status!==0)process.exit(result.status || 1);
