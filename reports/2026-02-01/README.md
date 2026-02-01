# Dataset 2026-02-01

## Source
- **Platform:** Moltbook (https://moltbook.com)
- **API:** Public API v1
- **Collection:** Hourly scans of hot/new posts + full comment trees

## Coverage
- Posts: 4535
- Actors: 3202
- Comments: 24,167
- Interactions: 138,732

## Known Biases
1. **Selection bias:** Only public posts collected
2. **Temporal bias:** Scan frequency may miss short-lived content
3. **Platform bias:** Moltbook-specific agent population
4. **Observer effect:** Agents may know they are being studied

## Limitations
- No access to private messages or deleted content
- Vote counts may include manipulation
- Actor classification is probabilistic
- Network centrality on visible interactions only

## Data Quality Notes
- Prompt injections detected: 621
- Encoding: UTF-8
- License: CC BY 4.0

## Files
| File | Description |
|------|-------------|
| daily_report.md | Main ethnographic report |
| metadata.json | Full dataset documentation |
| raw/posts.csv | All posts with metrics |
| raw/network.csv | Interaction graph |
| raw/memes.csv | Viral phrases |
| raw/actors.csv | Actor profiles |
| raw/conflicts.csv | Disputes |

## Citation
```
Noosphere Project (2026-02-01). Daily Field Report.
https://noosphereproject.com
```

## Contact
- Website: https://noosphereproject.com
- Email: noosphereproject@proton.me
- Moltbook: @NoosphereProject
- Twitter: @NoosphereProj
