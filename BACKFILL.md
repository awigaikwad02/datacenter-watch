# News backfill report

Generated 2026-10-26T02:13:06+00:00. Range 2024-10-01 to 2026-10-14 in 14-day windows (complete).

- Requests: 957 (0 failed)
- Headlines fetched: 36950; passed the filters: 29436; new to the archive: 17116
- Archive: 1765 headlines before, 19695 after; earliest 2019-11-18
- Operational records with a completion date (from a headline) in the last 24 months: 26
- Records lost: 0; attached headlines lost: 0
- Records to review (headlines from two different companies): 5 (see `data/registry_review.json`)

## Headlines per month and query

Fetched / passed the filters / new to the archive, by the month the window starts in.

| Month | announced | cancelled | construction | hyperscaler | operational | Archive total |
|---|---|---|---|---|---|---|
| 2024-10 | 361 / 234 / 149 | 83 / 16 / 6 | 108 / 36 / 29 | 121 / 53 / 13 | 239 / 101 / 85 | 207 |
| 2024-11 | 307 / 233 / 152 | 72 / 15 / 8 | 73 / 29 / 24 | 68 / 45 / 6 | 108 / 60 / 51 | 204 |
| 2024-12 | 220 / 146 / 96 | 64 / 7 / 2 | 58 / 21 / 12 | 60 / 31 / 7 | 122 / 55 / 45 | 230 |
| 2025-01 | 497 / 309 / 180 | 96 / 9 / 1 | 57 / 26 / 19 | 92 / 33 / 4 | 188 / 85 / 76 | 299 |
| 2025-02 | 405 / 269 / 178 | 73 / 23 / 11 | 65 / 37 / 28 | 73 / 40 / 13 | 133 / 55 / 52 | 276 |
| 2025-03 | 339 / 236 / 159 | 70 / 9 / 2 | 71 / 33 / 20 | 75 / 36 / 11 | 144 / 73 / 64 | 283 |
| 2025-04 | 453 / 332 / 243 | 117 / 41 / 16 | 97 / 28 / 19 | 110 / 46 / 16 | 156 / 78 / 70 | 272 |
| 2025-05 | 450 / 304 / 195 | 94 / 33 / 5 | 85 / 36 / 28 | 92 / 41 / 12 | 182 / 85 / 76 | 271 |
| 2025-06 | 475 / 285 / 185 | 56 / 26 / 6 | 64 / 32 / 22 | 64 / 26 / 9 | 98 / 39 / 35 | 326 |
| 2025-07 | 331 / 242 / 182 | 77 / 38 / 21 | 29 / 22 / 18 | 75 / 42 / 21 | 146 / 81 / 68 | 346 |
| 2025-08 | 580 / 457 / 303 | 94 / 44 / 27 | 94 / 49 / 39 | 92 / 54 / 12 | 190 / 99 / 86 | 479 |
| 2025-09 | 1180 / 947 / 531 | 98 / 91 / 44 | 79 / 50 / 43 | 113 / 71 / 17 | 154 / 103 / 92 | 576 |
| 2025-10 | 1166 / 947 / 521 | 96 / 65 / 26 | 95 / 68 / 62 | 92 / 51 / 11 | 177 / 89 / 81 | 642 |
| 2025-11 | 943 / 764 / 465 | 120 / 108 / 71 | 54 / 39 / 31 | 69 / 39 / 12 | 152 / 73 / 65 | 716 |
| 2025-12 | 691 / 610 / 380 | 149 / 138 / 67 | 23 / 19 / 14 | 59 / 35 / 9 | 121 / 82 / 73 | 645 |
| 2026-01 | 905 / 813 / 502 | 134 / 130 / 78 | 90 / 66 / 54 | 96 / 50 / 23 | 182 / 102 / 95 | 729 |
| 2026-02 | 598 / 534 / 435 | 326 / 314 / 176 | 100 / 84 / 75 | 47 / 33 / 5 | 93 / 68 / 65 | 727 |
| 2026-03 | 1918 / 1721 / 955 | 429 / 391 / 210 | 110 / 79 / 67 | 136 / 94 / 45 | 239 / 165 / 145 | 1090 |
| 2026-04 | 1148 / 1057 / 590 | 650 / 625 / 341 | 70 / 58 / 50 | 84 / 49 / 23 | 88 / 63 / 58 | 1196 |
| 2026-05 | 1273 / 1174 / 558 | 733 / 728 / 315 | 203 / 169 / 77 | 68 / 44 / 8 | 143 / 91 / 77 | 862 |
| 2026-06 | 772 / 690 / 275 | 434 / 425 / 212 | 138 / 112 / 18 | 93 / 60 / 5 | 93 / 69 / 43 | 1571 |
| 2026-07 | 1079 / 989 / 582 | 534 / 526 / 299 | 177 / 126 / 111 | 164 / 110 / 70 | 150 / 115 / 92 | 1301 |
| 2026-08 | 1404 / 1321 / 814 | 980 / 960 / 478 | 170 / 137 / 118 | 92 / 58 / 32 | 107 / 85 / 67 | 1489 |
| 2026-09 | 2916 / 2625 / 1573 | 2274 / 2186 / 956 | 291 / 221 / 183 | 127 / 81 / 28 | 371 / 271 / 207 | 2132 |
| 2026-10 | 61 / 51 / 11 | 100 / 99 / 22 | 46 / 33 / 14 | 51 / 30 / 13 | 89 / 50 / 34 | 2732 |

## Registry before and after

| | Before | After |
|---|---|---|
| Records (visible) | 73 (73) | 504 (504) |
| Announced | 31 | 349 |
| Cancelled / Blocked | 3 | 32 |
| Operational | 23 | 53 |
| Under construction | 16 | 70 |
| Confidence high | 4 | 61 |
| Confidence low | 10 | 112 |
| Confidence medium | 59 | 331 |
| Umbrellas | | 112 |

## Operational projects created by the backfill (29)

| State | Project | Place | Completed | Headline |
|---|---|---|---|---|
| AL | [Meta Huntsville data center](https://therackreport.org/projects/meta-huntsville-al-2026/) | Huntsville, Alabama | 2026-10-21 | [Meta opens Huntsville data center doors amid local concerns over water and power use](https://news.google.com/rss/articles/CBMijAFBVV95cUxQOHQ2blIyN3ZodWlranpSVGRNaUd3UFNIbnVZOGhIUXptVHdrSlEzUHRlNktlbHh3MjFMZ2xUR29acHl1WjZ5dDNiRkNpaHdVcmVlbU0yS25VWS1DbTItWXF2aERxeUd2Wjdnb3pOWWtpUGxDMEwzMkNUNXNWM3F3SFd3VU81eTVjR2tULQ?oc=5) |
| AZ | [Meta Mesa data center](https://therackreport.org/projects/meta-mesa-az-2025/) | Mesa, Arizona | 2025-01-30 | [Meta’s Mesa, Arizona, data center comes online](https://news.google.com/rss/articles/CBMikAFBVV95cUxPUGQ2ME1FZ2l6ejJ3VjhZZ1Ywczd4bV81VmxNX19ocXJ0ZndQZHhmV1M3MV9oSDhQckFVdFV4LW9UWl9vU3pMMXJJRzlMLXkySWVfX2ZnMjdtMWdvRmM3MVdSNmY0bkgwcVRiRXR2OE1wbnc2eVhwdDRTamV2S1d5MEMyb1ltLVFlRl9tLWVXWkc?oc=5) |
| CA | [Santa Clara data center](https://therackreport.org/projects/site-santa-clara-ca-2024/) | Santa Clara, California | 2024-11-19 | [Colovore Opens Second 9MW High-Density, Liquid-Cooled Data Center in Santa Clara](https://news.google.com/rss/articles/CBMi0gFBVV95cUxOQ2RqR2kwdFoySy02NnNOU1hrWnlTc3kxMkRWQTlqc205WFpyWVlFZFBkLXE5ZDE4WVRFS25VSWZxQXpTcjZtTmN2SEhzcldLeFBwOHBIbzc1WllBZjJvLTRhb2N2Q21mQXFRRzY1bEY0VnktQUdDbDgxbC1mSTdFc0IzYTVsZnNrQk9GdUhScjdXNFNTWDZMX0FJYmdjRlg3NUQwNy11blNxbHlaNElpWmdKNUt6NVJKM3hpTE5zQ3NIRVQ2MXlYR0lPLVRCSFhkNGc?oc=5) |
| CA | [EdgeCore Silicon Valley data center](https://therackreport.org/projects/edgecore-silicon-valley-ca-2025/) | Silicon Valley, California | 2025-09-19 | [EdgeCore opens Silicon Valley data center](https://news.google.com/rss/articles/CBMijgFBVV95cUxQcWpyLW1PaFV5cDRtU0FmTmxxX1B3aWZsNy15ZWYtMHVDdUg1blpRbnlWUE5EYXJFZUNkTTExeVE4ZUtQbGtaZmhnLWZmdGVNMEE3WGd3a1RSeC1JOVZKenVwT1U5Q2NadlotMml4NUowZFRLOUR2YWpRTlBGYnltc1lVNng5VngyYmtFV2hB?oc=5) |
| GA | [Flexential Atlanta data center](https://therackreport.org/projects/flexential-atlanta-ga-2025/) | Atlanta, Georgia | 2025-05-14 | [Flexential Completes Atlanta Data Center Purchase](https://news.google.com/rss/articles/CBMikgFBVV95cUxPY09tdlJJTmVDa1NOTEtXb0JDN2x1YnJkR2pSaElDdTVZWG5RaFZVVWZWSjRmMGEtc3VxdEJSalZBdW5YSVhXNmVaY2VoQ1FSRkVZdUh4dC14NkpiMm9KY0w4NmlSMHg4bS1XYmFibk5jQWJXSlhFbUtXRnhmSXdrN3RSTGo5RVF0VFprNUxoVUNhUQ?oc=5) |
| IA | [Apple, Iowa (site not yet named)](https://therackreport.org/projects/apple-ia-unnamed/) | Iowa | 2024-10-16 | [Seven years on, Waukee, Iowa's Apple data center finally opens](https://news.google.com/rss/articles/CBMimwFBVV95cUxOTExyLXdjWlhWWmxHM1dmSk5CWWNEdmUta0RHOEZLT1k2Rm82SmZnTVRrYld4WWJxYWJ6RVhXOUQxeUJEcl9LZHJrcEZtRlcwUkxjd0F3Z3Zidkg5ZGRHWTFlNV9MNUlGbmF0bHFmVVpONXRaYllfazFYcXRmUHNRY0wwUVVRNmwzcU03d0Ewb2pDOWJHa0xpdEpTOA?oc=5) |
| IA | [QTS, Iowa (site not yet named)](https://therackreport.org/projects/qts-ia-unnamed/) | Iowa | 2025-12-23 | [CBJ Newsmakers: First QTS data center buildings near completion](https://news.google.com/rss/articles/CBMilwFBVV95cUxNM0kwODVkb2lxZFNxcFlKdmxTY2ItZlJia0pWVXZtV1ZZVXctNFJwMnItX3E0SW5VTTZQQm10YXhJQnVEUFJYYlhzNjhobkhmQnR1WXNWaUFkOEFJTW9VTHpwb2M4SGVBeWMxMHFNTHlINW0yV0dpTmg4NWxxVnM1WGUtMjI3UUhDM1JMWEU4RDM2VDR3QmNj?oc=5) |
| IA | [Des Moines data center](https://therackreport.org/projects/site-des-moines-ia-2026/) | Des Moines, Iowa | 2026-10-13 | [Digi Power X Announces $200 Million Debt Financing Commitment to Support Completion of Alabama AI Data Center and Provides Expansion Update](https://news.google.com/rss/articles/CBMipwJBVV95cUxOZDNvVndsV1ZzMVAwN1RqOHNxZ0k2WklPY2V0bzNhNHNNNWpJRU1uTTVuUkJpOFh5ZkhmS2RzOXBCMFZQb0JqVXcwYmN3NnZnUm5uM2I4S3UwVW12M0lNdDdBSmc1R3MwUG1JcUoxOEdZcHZ6aS00ZllSUVBPU25TM3FLN0MwNDBwc3pZcTB1RDQ3ZFliX2hCVmM0cGFBb3VyMXJDcXhubWkyaWllYjVGcUhTbEFvWHFYZDZ4azNkZnBZNDU2RnlrWjdIZUVMZDY5Z3ZfMklmeUxtX1J4U2tUWmZWcVU3NGNJUmZLeE5IbFotTlgwQnAxQ20tLVdEQ204RXVFbEozYTJTUkE5NzdOa2xnal9DcjA4WnFNeGg4em5jYm5kc0pN?oc=5) |
| ID | [Meta, Idaho (site not yet named)](https://therackreport.org/projects/meta-id-unnamed/) | Idaho | 2024-10-25 | [Meta’s mega data center in Kuna on track to be completed by 2025](https://news.google.com/rss/articles/CBMiqwFBVV95cUxQNXRCZWhiWHAxWS1pYkZWbFh4eDF0ZnF6V3RWVk14eUNsUkJOTDhFYmJNVUtTVXg1OFRSaDdYTl9BbGJaTjdjcDdRUk5aTzRpZUpzNTFJY1pGWnNYMjFNS0RzbWoyRHBXYU43dGVtYlJsbnhsODNkNnRuT0lnbXl1N0Znb2lZTEVNWEVUSVhPaDZmRjJCUTQ4eUdJWmFGMjlpaTN3R191eGl1bWM?oc=5) |
| MO | [Meta Kansas City data center](https://therackreport.org/projects/meta-kansas-city-mo-2025/) | Kansas City, Missouri | 2025-08-20 | [Meta's latest data center campus goes live in Kansas City, Missouri](https://news.google.com/rss/articles/CBMirgFBVV95cUxOaWs1RXpfMjBodjk1OTdVNDUtX0RuLVZTVDJPTWVHUlhxbWdUb0VaaGx4ek02SFB5NEs2RGVfdUVjbVk5Sk4tMkpIVjcxZWR0Sm9wNk5yTk5aOHVzLXlTMGRhZlEzbGgySjAyQTdORVFHQV8zbWRYTmk4QWZqMGJTRWJGTVJycVVHTHZKR2QtX0xscVcwbFJQaC1ZQmE2bjBjVWdWOHpzb3dTMmVCMGc?oc=5) |
| MO | [Meta, Missouri (site not yet named)](https://therackreport.org/projects/meta-mo-unnamed/) | Missouri | 2025-08-20 | [Meta Data Center Opens; Represents $1B Investment in Missouri](https://news.google.com/rss/articles/CBMitgFBVV95cUxNS1g3bkg5LVlkcnRTYWVaeFQ1X194X3ZDaTlwaWVYNy1aWXk1ZlBEX3JLVDJsam81dnpnVTB3ZkRCaUZqNHlqYURjZU1CUVV2YVZnUnd5U2dpb1AzRzZEa3JjSXA1VGFZUGRyRXAtMnBhN1E4aWg2WVBROGktaDJZTndIVlJ6NDR0LUV6RFlkM2NrMUVhdnlZaUNtU3l5QTlwZU02YXhsWUxkOE55emN0V0xpalhWQQ?oc=5) |
| MS | [Amazon, Mississippi (site not yet named)](https://therackreport.org/projects/aws-ms-unnamed/) | Mississippi | 2026-06-09 | [Ribbon-cutting ceremony held for new Amazon data center in Clinton](https://news.google.com/rss/articles/CBMilwFBVV95cUxOX2lBNEg0VlNwQm92TFhkdEo1WGtCTEM1NGhjMXFKQ05kd3dvV29wRjlEb1plLUZYMjdiRnNfTHFiWEdXOXdlYmYzZVBjeFJtSjhqSTVZWnNucnJZSEFNNUlXM3FXb2RJdlRxTHFkZTlsd05ZZkxtUWdxbG1seHpCV2xzUTg2NFZ6NFFBdkVETjZRWFlCOXdZ?oc=5) |
| ND | [Applied Digital, North Dakota (site not yet named)](https://therackreport.org/projects/applied-digital-nd-unnamed/) | North Dakota | 2025-12-01 | [Applied Digital completes first data center building at North Dakota campus](https://news.google.com/rss/articles/CBMiuwFBVV95cUxQTllpNGxiV2dtU01BVF85OU9CRzhDMW02bHdJby16S3VCWmtpQU9BTzk1aTBGcXdTNld6Y1c0Rl91b25zQW9ZeDdDcUtzdzMtQWQtclUwZkctaWpkbkFldU5oYkVTRGQwX2dkbEZkd0NQb21JQl9KVTRNTXpxNllqNmFIcGFHb09BMmI5MzE1Ui1OMGVJaXZPdXZSSTBtbVBObEtQMDBWVGg4ZkE1TDE2RmxudXF2ZWtIa2RN?oc=5) |
| NV | [Novva Storey County data center](https://therackreport.org/projects/novva-storey-county-nv-2025/) | Storey County, Nevada | 2025-07-08 | [Novva opens 300,000-square-foot data center in Nevada's tech corridor in Storey County](https://news.google.com/rss/articles/CBMi_AFBVV95cUxPMDFobDVaLWVuQm9EeFk4Z1NVVF9VUFJaT3AtVTlUMG1Xb0t2c1RHMnhFOXUzX1Z2WlkzYU9fSU5sd3ZHX2F5SUV5cUFnd2hpQndDS3BlUGUtSUpJbTQ1TFJDNVg2eUtVNkpBa05pR3BMLVJCYTBvZUdoNXZMVkdtWk03bElqSHdzN3YycXI0R0Z5Y25JbmVQT1FRVDZOLXZMckpyTkJYOFJxSlphakJ5eklDd29UdXBseXNmQjV0Q1hBYWJpWHU2VXlzUFZQeVFncmhwMWltWGxOX1oxeW51VjVwNnNUZF9fbG0tZENVVmhHQlRjSFZXVVhxNHo?oc=5) |
| NV | [Novva Reno data center](https://therackreport.org/projects/novva-reno-nv-2025/) | Reno, Nevada | 2025-07-09 | [Novva data center with robot dog guard, drone monitoring completed near Reno](https://news.google.com/rss/articles/CBMi0AFBVV95cUxQSVlDQ1NhaDd6cWJWRkstVmh1M3d3SWt3UjM4eWI0RGZ5emR0cC1pUm1UNllqeVY2MV9PUUZ3emJjMzEyWm11SnNkX1ZvYTNhRURXOFNBZHJrNGZfV2lKX3RGaU82dWdvYk5nUkVMTktNRGZjYmlqVEI1Vms0d0hnU0lSWlREdUtzRklCM3Z5MW5YRDFQeUpPdXY4eUw4cnhjZ21OODZrNW9IbWNOQldmXzFSMzVZYTdzTEJuZXJiRDd4WUZEeEI2Y1h1aUdxNnVW?oc=5) |
| OH | [New Albany data center](https://therackreport.org/projects/site-new-albany-oh-2025/) | New Albany, Ohio | 2025-09-15 | [$246M AI-focused data center opens in New Albany](https://news.google.com/rss/articles/CBMikwFBVV95cUxQXzdZdUFycnB3a3lvaGVVZEdScElQOHduWXBhWWhmUTYtbHlwU1cwREFheVFLYnJfdnROMkg1SGkzZEx1Qnhrb1o0MU11X3paTklxbEM3YkdKNUZmaE1KNVhIS3JGMHRaLUNYSllGYjNsaDZEeTBZYmJNQ3dHbzU4RUoxbzRCWTZqckpIWnRuQUVnVGc?oc=5) |
| OK | [Oklahoma City data center](https://therackreport.org/projects/site-oklahoma-city-ok-2025/) | Oklahoma City, Oklahoma | 2025-09-23 | [Cerebras opens 10MW data center in Oklahoma City](https://news.google.com/rss/articles/CBMilwFBVV95cUxQUnByNkoybzNmd20zcGNndHdwMS1RWVJZdWU1UDRmUVlUTEZkVHUyYWlhTFpMY21jMmtkT1ZXX0RNTWFSYTRpM3Z2ekhjdlZtcUNFY2lTT1VvU2pxQnFhdFBPcEJheDR6eGg2Uzhpc3BSTVV3eU85OUR3NXVzTnM5MXhaZ09JdkVaQnNBMkZqWmQ4eXF2eVNR?oc=5) |
| OK | [Crusoe Tulsa data center](https://therackreport.org/projects/crusoe-tulsa-ok-2026/) | Tulsa, Oklahoma | 2026-09-14 | [Crusoe Opens Second Tulsa Plant to Build AI Data Center Components](https://news.google.com/rss/articles/CBMikgFBVV95cUxOVUJ1Uy04UnF1LUxZd1FpeVg3dUhHcDA1d3NVREVNSFFsMld0S005QTFQaGJ0VENXQlUtWlFuc0xWTi05aWxkRUx4X0ZWblZkV29vWng0b0ZaZHVybTNiOC1Bd1dmZm1uTHhNcDdYSFlpNEVJc1psckY3bzM2ZDZlWTdBZkNtZUJoS1FCZ19FTUlMUQ?oc=5) |
| OR | [Meta, Oregon (site not yet named)](https://therackreport.org/projects/meta-or-unnamed/) | Oregon | 2026-06-03 | [Big solar tied to Meta data center needs comes online in Oregon](https://news.google.com/rss/articles/CBMilwFBVV95cUxOT3cyZ1llQzdOc24tMlVuTkdHQmdTYlBqXzBxdmx2Vnc4UmV2akhoaTRiSmJVa0NfSGZGZzBiZU9hRUs1ZHlCN0FXNjBJLXdrRnR5dVZ2bVhPcEdHbi1uN3Fld1JvLU5PT29OVzhYRHN0ZFp2Q0NxVmF2dE1zNWM2bmtsX2xNamN1ZnM4R1F4SDVMX291cWE4?oc=5) |
| SC | [Orangeburg County data center](https://therackreport.org/projects/site-orangeburg-county-sc-2025/) | Orangeburg County, South Carolina | 2025-12-16 | [Data center supplier opens $7.4M factory in rural Orangeburg County](https://news.google.com/rss/articles/CBMiqAFBVV95cUxQQVdzV0p5NTVtdlM5bV9fZldLVGR4NnQ5ZzZ5WWVlUWg5M1BvYk1VbkNxczBuYWV1TUpsUFA4UlVUUWtkaE0xSGs0YklsXzRFM01fZEVNQ1EtcTVFblJvUExucDNJVlBYYWFSSXhjdHpndF9kRWFpbDRuT0JSVlkwSVROcnNmazRDSVJOZWpFODJGNnl6X0R1c0Y4TFVibkhHRThOS25WWDc?oc=5) |
| TN | [xAI, Tennessee (site not yet named)](https://therackreport.org/projects/xai-tn-unnamed/) | Tennessee | 2026-04-10 | [Mayor, MLGW push xAI to complete water recycling facility](https://news.google.com/rss/articles/CBMingFBVV95cUxOMFpqVm9RZ3ZvNG9vaHVPTDAyY29WSHJnd1BWZkRiVlFVNEUyclRsLVlaTDFLQW03d213UmJZTnNCSGRQSTJfUjM3SHVKakJrd2dIZ0FyVWpiTGQ3SG9GLWxCbXJkVFluX3dOakpxeWIwQ3I0YmdmVDRBUTZuVENBX3QyblozSGY3RmhzbklpU1FiTFY5MUlnUkhteGF3Z9IBowFBVV95cUxNM0t6amgxSVJJOTF5WWVRWUtsZUVMdnlwVGVjR01WbFdkT1IzVEVRYzdjWkxubW9BckdObTJnaHR1UGJfVWhCR25ZdDducUQ2bU5zSWp1dWdJYnhpQlVFMzBrMzZsQWdtQVdqWmt3Rzk5RWJjeWw1MTdTMnJURzdyU3pfRTRfam9nUTA2dGlrUGFJLTUwMHd4LUdLVW92LS1VQ213?oc=5) |
| TX | [Sabey Austin data center](https://therackreport.org/projects/sabey-austin-tx-2024/) | Austin, Texas | 2024-10-17 | [Sabey Data Centers Completes Construction at Austin, Texas Data Center Site](https://news.google.com/rss/articles/CBMiywFBVV95cUxOenEyLUFQZFZ3UmdUU0NvZ1ljTWc0TktxVUdoaHlvZXo2SXRZeTBzRXRHUl84SEo5dDZnNjlQaDFybmMta05qWGJhWXVjcWJnNlAydjhYdldsN1NGNkI0d3RENE11VF9EbG1FLU15aHJOLTVWYnQ2dDlEME05QlVpdWJkZVQ3d3lBMGRmeGtKOXVZV051b2lBV013Y29CUnk4cWRuOU5sM3U5VGJmbGtNaUNfSGNSNUVoWVV5RnhJM2VmalJJTDBVOHhudw?oc=5) |
| TX | [Google, Texas (site not yet named)](https://therackreport.org/projects/google-tx-unnamed/) | Texas | 2024-10-21 | [Massive Texas solar farm opens to power Google data centers](https://news.google.com/rss/articles/CBMilwFBVV95cUxNXzZGLWNFTURhRXA0SW1Xcm0zRm9ENWRhTVZwWWpiLXdMYjYtM0d2cllRc1NiWk9ZcEpYSlJSWU1GOXBCNEdRVFVzQ2JTNVpSYm1PZ09RcU9wczZmOUZXQy1saEpzU2RzMmRvZVNVTUNMZEpFc3U0UFVlazNUdk8wdG91TTAtMjE1bjRSR3lwWUhmVXVaSGhV?oc=5) |
| TX | [Fort Worth data center](https://therackreport.org/projects/site-fort-worth-tx-2025/) | Fort Worth, Texas | 2025-03-06 | [Siemens Opens $190M Fort Worth Manufacturing Hub to Build Equipment Powering America’s AI/Data Center Infrastructure](https://news.google.com/rss/articles/CBMiiwFBVV95cUxNOE54X25rckhBVnhmMms2aTVDOVJmNjlXczlpMVM4eUI4TUV0OVhZajVUaVRMQkVweEtPNmJBdmY3aWF6Ylo2bTlvdnB6ZjU2MWhpYmRLV0pYS3lSLUdZTjZ6NlpIT2tTNURoMFpRYXJyOUVlSFRYUzI1UkFYUGVUeU15ZmJlS1NDYjI0?oc=5) |
| TX | [Compass Datacenters Dallas data center](https://therackreport.org/projects/compass-datacenters-dallas-tx-2025/) | Dallas, Texas | 2025-05-27 | [News \| Compass Datacenters lands loan backed by newly completed data center in Dallas area](https://news.google.com/rss/articles/CBMiwgFBVV95cUxPNFZhQnBNODBOY1V6RE9ZWmJ3ckZJeVk0eTE5OGlIcS14MFZMQjNFY0tuTVhPbmdJdXRfeVJoNDRxWXoxNlI0a0gtd3lXTFd1dDM0V2hrc2stbkJOb0xTWDhXUmt0bTBPWU80dzJuNmRmckNOdWl3LTk2cU1kR1lEUWlPREFZY2VybWZWZ0p2dGJTUnhJeTZXcXRVV3RSUlRkbENGRWRxX1VSMDJlZnllU3l0OXJ4ZjJHczhKVjJSRzdLUQ?oc=5) |
| TX | [Meta, Texas (site not yet named)](https://therackreport.org/projects/meta-tx-unnamed/) | Texas | 2026-08-05 | [$1.2B Meta Data Center Opens in Temple](https://news.google.com/rss/articles/CBMie0FVX3lxTE1TdG9GSGFTRTR1cHNIaVNJUmdIMF9vNTJkWDlDTGdqQVB1RjYwODhjS0lsN1oydDRMMjlna1ZYNk1SbXRCbG9FMkNvZlYzTV9NQ2VwNVctWkMtVDVrSGNLQ0tnV3BHaEZ1aHhWcVhHSUdiZlB3eFRXdlpRaw?oc=5) |
| UT | [Novva, Utah (site not yet named)](https://therackreport.org/projects/novva-ut-unnamed/) | Utah | 2025-03-13 | [Novva Secures $2B to Complete Utah Data Center Campus Construction](https://news.google.com/rss/articles/CBMiogFBVV95cUxORDc1b0piVmczenUzMms0dW5PMWxpamVJWTlzU0pOMVRKd3pvcWstWC1MdlBCUnJBUG1SRWFsdldpcUYzVWxpdDJ5cm9ka2F5cXJxelA0MFM1UGlyRmtEblcwQmtnY1RQdjdGVkt4ZHkxTmxjVjZhRlhLbXJHczNxajdRMHNQM3EwVUltSE1GbmJ5RzFMaFFkcjkxbUZCcVQ1cUE?oc=5) |
| VA | [STACK, Virginia (site not yet named)](https://therackreport.org/projects/stack-va-unnamed/) | Virginia | 2026-05-28 | [Stack Infrastructure completes first building at 1GW Virginia data center campus](https://news.google.com/rss/articles/CBMigwJBVV95cUxOTWg3VkRBNXM3RW1rVGtfX25tSXNpRHpfcXZ5NjZINllSMUs5WVNoR3Jka3oxNlRQLWxWZXJIQXhGYWhrUWpnTTBGMG1zMU5tMWZGY196a3lYcTFld0NqWDdqYVRqUnVocTliaVpUNndXRzZSVWdPVEVxWThtVzVRWWUyOUE4ZTFxSEp1NUxBMFFQZjNDdmZwTS1lQnJTUUlCVVk4ZG0yRHJZYjRLeGF6V3kxVjNLRm50Wl9tXzY2WTVJbVZZS3BLaDlXMWdyRFNYWEhjWXp5UzlQVUY2WmVpTDRzdHlSQXNXOHQyaWZybEIyT3VfelB3NUZnUXFoazQ2UVRB0gGIAkFVX3lxTE9pUWJWNjhaNU56ZWlKZE80Vy16d0NkUkg5MVhTeWYxT3BTSEVnV0ZfRGhLZFMwTktzYURnYVQ1UGl4ai1WcFZDVE5UV0lCbE9lV2NJVktfczlDb3h6aThNTU1EU0dDdHlPdXhFRzl0cmV5cDJmRnNDQWxsSjJ6ODd6TVlRZWg5RUI1c2RGT2FoN2QweHN1MFdHZTJMQ0VVemlXRDMwWG1WUFJGM040MnpnLWFoQXhOSGM0WURhR2NsWVc4U05jR1ZjRkQyRnJOaWRkR2ZNdFg0Q0h3TjVIcTBTMGVLbzl0aUFITWJfbjVXNjduaHBRTkRBdER0RTlWLVhUUExZZk54UA?oc=5) |
| WA | [Amazon Walla Walla County data center](https://therackreport.org/projects/aws-walla-walla-county-wa-2026/) | Walla Walla County, Washington | 2026-08-25 | [Amazon completes its application for a data center in Walla Walla County](https://news.google.com/rss/articles/CBMihwJBVV95cUxNZGZwNzBkbUVTU3lGalpHVFd6eFNlY0IwYkRJY01RZHhTcHB1VFg2Y2NGUkZDM0hXdDZIWE5nVjFfTlo1NVZIcExxVFZGZE1yMzM2SjgtOFBCWUltUHJGblR3WGNLUlZ6aGRDMmN4bWFUTFBQQWhqcGNoNGhqV1JIeFh3MkhTYlhSc0wtRXpvYWYyUHFXbEFwU3BBejVmQkhDS05sdjlncVFwSmFfU2pEeXllc1AxNjl2MjlJd1lpM0pXVFk4cThWSlVWelBsT0NNS1p1aF9QTlRMdzExR0lHUnByWVNmYVNnZXJVMjlLV1hYbmZvdmlvUVo3R0dUYzVLVUlTTDVxUQ?oc=5) |

## 30 largest projects by MW

| # | Project | State | Status | MW | Source |
|---|---|---|---|---|---|
| 1 | [Project Matador](https://therackreport.org/projects/project-matador/) | TX | Announced | 11,000 | curated |
| 2 | [Amarillo data center](https://therackreport.org/projects/site-amarillo-tx-2025/) | TX | Announced | 11,000 | detected, medium |
| 3 | [SoftBank, Ohio (site not yet named)](https://therackreport.org/projects/softbank-oh-unnamed/) | OH | Announced | 10,000 | detected, low |
| 4 | [Lea County data center](https://therackreport.org/projects/site-lea-county-nm-2025/) | NM | Announced | 7,000 | detected, medium |
| 5 | [Meta, Louisiana (site not yet named)](https://therackreport.org/projects/meta-la-unnamed/) | LA | Under construction | 5,000 | detected, low |
| 6 | [Port Washington data center](https://therackreport.org/projects/site-port-washington-wi-2025/) | WI | Announced | 3,500 | detected, medium |
| 7 | [OpenAI Atlanta data center](https://therackreport.org/projects/openai-atlanta-ga-2026/) | GA | Announced | 3,200 | detected, high |
| 8 | [OpenAI Effingham County data center](https://therackreport.org/projects/openai-effingham-county-ga-2026/) | GA | Announced | 3,200 | detected, high |
| 9 | [Ascension Parish data center](https://therackreport.org/projects/site-ascension-parish-la-2026/) | LA | Announced | 2,880 | detected, medium |
| 10 | [Google, Wyoming (site not yet named)](https://therackreport.org/projects/google-wy-unnamed/) | WY | Announced | 2,100 | detected, low |
| 11 | [Hyperion](https://therackreport.org/projects/hyperion/) | LA | Under construction | 2,000 | curated |
| 12 | [Microsoft, Texas (site not yet named)](https://therackreport.org/projects/microsoft-tx-unnamed/) | TX | Announced | 2,000 | detected, low |
| 13 | [Detroit data center](https://therackreport.org/projects/site-detroit-mi-2026-2/) | MI | Announced | 2,000 | detected, medium |
| 14 | [Phoenix data center](https://therackreport.org/projects/site-phoenix-az-2026-2/) | AZ | Under construction | 2,000 | detected, medium |
| 15 | [Crusoe Cheyenne](https://therackreport.org/projects/crusoe-cheyenne/) | WY | Announced | 1,800 | curated |
| 16 | [Crusoe, Wyoming (site not yet named)](https://therackreport.org/projects/crusoe-wy-unnamed/) | WY | Cancelled / Blocked | 1,800 | detected, low |
| 17 | [Core Scientific, Texas (site not yet named)](https://therackreport.org/projects/core-scientific-tx-unnamed/) | TX | Announced | 1,500 | detected, low |
| 18 | [Frontier](https://therackreport.org/projects/frontier/) | TX | Under construction | 1,400 | curated |
| 19 | [Stargate Michigan](https://therackreport.org/projects/stargate-michigan/) | MI | Announced | 1,400 | curated |
| 20 | [OpenAI, Texas (site not yet named)](https://therackreport.org/projects/openai-tx-unnamed/) | TX | Under construction | 1,400 | detected, low |
| 21 | [Oracle, Michigan (site not yet named)](https://therackreport.org/projects/oracle-mi-unnamed/) | MI | Announced | 1,300 | detected, low |
| 22 | [Stargate Abilene](https://therackreport.org/projects/stargate-abilene/) | TX | Under construction | 1,200 | curated |
| 23 | [Irwin County data center](https://therackreport.org/projects/site-irwin-county-ga-2026/) | GA | Announced | 1,200 | detected, medium |
| 24 | [Colossus 2](https://therackreport.org/projects/colossus-2/) | TN | Under construction | 1,000 | curated |
| 25 | [Meta El Paso](https://therackreport.org/projects/meta-el-paso/) | TX | Under construction | 1,000 | curated |
| 26 | [Prometheus](https://therackreport.org/projects/prometheus/) | OH | Under construction | 1,000 | curated |
| 27 | [Stargate Port Washington (Lighthouse)](https://therackreport.org/projects/stargate-port-washington-lighthouse/) | WI | Announced | 1,000 | curated |
| 28 | [Crusoe, Texas (site not yet named)](https://therackreport.org/projects/crusoe-tx-unnamed/) | TX | Under construction | 1,000 | detected, low |
| 29 | [Google Detroit data center](https://therackreport.org/projects/google-detroit-mi-2026/) | MI | Announced | 1,000 | detected, high |
| 30 | [Google, Texas (site not yet named)](https://therackreport.org/projects/google-tx-unnamed/) | TX | Operational | 1,000 | detected, low |

## Likely false Operational steps (13)

The headline that moved these to Operational is about a purchase, an application, a factory, solar power or a completion still to come. Fix with `set_status` in `data/project_overrides.json`, or tighten the Operational rule.

| Record | Headline |
|---|---|
| `aws-walla-walla-county-wa-2026` | [Amazon completes its application for a data center in Walla Walla County](https://news.google.com/rss/articles/CBMihwJBVV95cUxNZGZwNzBkbUVTU3lGalpHVFd6eFNlY0IwYkRJY01RZHhTcHB1VFg2Y2NGUkZDM0hXdDZIWE5nVjFfTlo1NVZIcExxVFZGZE1yMzM2SjgtOFBCWUltUHJGblR3WGNLUlZ6aGRDMmN4bWFUTFBQQWhqcGNoNGhqV1JIeFh3MkhTYlhSc0wtRXpvYWYyUHFXbEFwU3BBejVmQkhDS05sdjlncVFwSmFfU2pEeXllc1AxNjl2MjlJd1lpM0pXVFk4cThWSlVWelBsT0NNS1p1aF9QTlRMdzExR0lHUnByWVNmYVNnZXJVMjlLV1hYbmZvdmlvUVo3R0dUYzVLVUlTTDVxUQ?oc=5) |
| `compass-datacenters-dallas-tx-2025` | [News \| Compass Datacenters lands loan backed by newly completed data center in Dallas area](https://news.google.com/rss/articles/CBMiwgFBVV95cUxPNFZhQnBNODBOY1V6RE9ZWmJ3ckZJeVk0eTE5OGlIcS14MFZMQjNFY0tuTVhPbmdJdXRfeVJoNDRxWXoxNlI0a0gtd3lXTFd1dDM0V2hrc2stbkJOb0xTWDhXUmt0bTBPWU80dzJuNmRmckNOdWl3LTk2cU1kR1lEUWlPREFZY2VybWZWZ0p2dGJTUnhJeTZXcXRVV3RSUlRkbENGRWRxX1VSMDJlZnllU3l0OXJ4ZjJHczhKVjJSRzdLUQ?oc=5) |
| `crusoe-tulsa-ok-2026` | [Crusoe Opens Second Tulsa Plant to Build AI Data Center Components](https://news.google.com/rss/articles/CBMikgFBVV95cUxOVUJ1Uy04UnF1LUxZd1FpeVg3dUhHcDA1d3NVREVNSFFsMld0S005QTFQaGJ0VENXQlUtWlFuc0xWTi05aWxkRUx4X0ZWblZkV29vWng0b0ZaZHVybTNiOC1Bd1dmZm1uTHhNcDdYSFlpNEVJc1psckY3bzM2ZDZlWTdBZkNtZUJoS1FCZ19FTUlMUQ?oc=5) |
| `flexential-atlanta-ga-2025` | [Flexential Completes Atlanta Data Center Purchase](https://news.google.com/rss/articles/CBMikgFBVV95cUxPY09tdlJJTmVDa1NOTEtXb0JDN2x1YnJkR2pSaElDdTVZWG5RaFZVVWZWSjRmMGEtc3VxdEJSalZBdW5YSVhXNmVaY2VoQ1FSRkVZdUh4dC14NkpiMm9KY0w4NmlSMHg4bS1XYmFibk5jQWJXSlhFbUtXRnhmSXdrN3RSTGo5RVF0VFprNUxoVUNhUQ?oc=5) |
| `google-tx-unnamed` | [Massive Texas solar farm opens to power Google data centers](https://news.google.com/rss/articles/CBMilwFBVV95cUxNXzZGLWNFTURhRXA0SW1Xcm0zRm9ENWRhTVZwWWpiLXdMYjYtM0d2cllRc1NiWk9ZcEpYSlJSWU1GOXBCNEdRVFVzQ2JTNVpSYm1PZ09RcU9wczZmOUZXQy1saEpzU2RzMmRvZVNVTUNMZEpFc3U0UFVlazNUdk8wdG91TTAtMjE1bjRSR3lwWUhmVXVaSGhV?oc=5) |
| `meta-id-unnamed` | [Meta’s mega data center in Kuna on track to be completed by 2025](https://news.google.com/rss/articles/CBMiqwFBVV95cUxQNXRCZWhiWHAxWS1pYkZWbFh4eDF0ZnF6V3RWVk14eUNsUkJOTDhFYmJNVUtTVXg1OFRSaDdYTl9BbGJaTjdjcDdRUk5aTzRpZUpzNTFJY1pGWnNYMjFNS0RzbWoyRHBXYU43dGVtYlJsbnhsODNkNnRuT0lnbXl1N0Znb2lZTEVNWEVUSVhPaDZmRjJCUTQ4eUdJWmFGMjlpaTN3R191eGl1bWM?oc=5) |
| `meta-or-unnamed` | [Big solar tied to Meta data center needs comes online in Oregon](https://news.google.com/rss/articles/CBMilwFBVV95cUxOT3cyZ1llQzdOc24tMlVuTkdHQmdTYlBqXzBxdmx2Vnc4UmV2akhoaTRiSmJVa0NfSGZGZzBiZU9hRUs1ZHlCN0FXNjBJLXdrRnR5dVZ2bVhPcEdHbi1uN3Fld1JvLU5PT29OVzhYRHN0ZFp2Q0NxVmF2dE1zNWM2bmtsX2xNamN1ZnM4R1F4SDVMX291cWE4?oc=5) |
| `novva-ut-unnamed` | [Novva Secures $2B to Complete Utah Data Center Campus Construction](https://news.google.com/rss/articles/CBMiogFBVV95cUxORDc1b0piVmczenUzMms0dW5PMWxpamVJWTlzU0pOMVRKd3pvcWstWC1MdlBCUnJBUG1SRWFsdldpcUYzVWxpdDJ5cm9ka2F5cXJxelA0MFM1UGlyRmtEblcwQmtnY1RQdjdGVkt4ZHkxTmxjVjZhRlhLbXJHczNxajdRMHNQM3EwVUltSE1GbmJ5RzFMaFFkcjkxbUZCcVQ1cUE?oc=5) |
| `qts-ia-unnamed` | [CBJ Newsmakers: First QTS data center buildings near completion](https://news.google.com/rss/articles/CBMilwFBVV95cUxNM0kwODVkb2lxZFNxcFlKdmxTY2ItZlJia0pWVXZtV1ZZVXctNFJwMnItX3E0SW5VTTZQQm10YXhJQnVEUFJYYlhzNjhobkhmQnR1WXNWaUFkOEFJTW9VTHpwb2M4SGVBeWMxMHFNTHlINW0yV0dpTmg4NWxxVnM1WGUtMjI3UUhDM1JMWEU4RDM2VDR3QmNj?oc=5) |
| `site-des-moines-ia-2026` | [Digi Power X Announces $200 Million Debt Financing Commitment to Support Completion of Alabama AI Data Center and Provides Expansion Update](https://news.google.com/rss/articles/CBMipwJBVV95cUxOZDNvVndsV1ZzMVAwN1RqOHNxZ0k2WklPY2V0bzNhNHNNNWpJRU1uTTVuUkJpOFh5ZkhmS2RzOXBCMFZQb0JqVXcwYmN3NnZnUm5uM2I4S3UwVW12M0lNdDdBSmc1R3MwUG1JcUoxOEdZcHZ6aS00ZllSUVBPU25TM3FLN0MwNDBwc3pZcTB1RDQ3ZFliX2hCVmM0cGFBb3VyMXJDcXhubWkyaWllYjVGcUhTbEFvWHFYZDZ4azNkZnBZNDU2RnlrWjdIZUVMZDY5Z3ZfMklmeUxtX1J4U2tUWmZWcVU3NGNJUmZLeE5IbFotTlgwQnAxQ20tLVdEQ204RXVFbEozYTJTUkE5NzdOa2xnal9DcjA4WnFNeGg4em5jYm5kc0pN?oc=5) |
| `site-fort-worth-tx-2025` | [Siemens Opens $190M Fort Worth Manufacturing Hub to Build Equipment Powering America’s AI/Data Center Infrastructure](https://news.google.com/rss/articles/CBMiiwFBVV95cUxNOE54X25rckhBVnhmMms2aTVDOVJmNjlXczlpMVM4eUI4TUV0OVhZajVUaVRMQkVweEtPNmJBdmY3aWF6Ylo2bTlvdnB6ZjU2MWhpYmRLV0pYS3lSLUdZTjZ6NlpIT2tTNURoMFpRYXJyOUVlSFRYUzI1UkFYUGVUeU15ZmJlS1NDYjI0?oc=5) |
| `site-orangeburg-county-sc-2025` | [Data center supplier opens $7.4M factory in rural Orangeburg County](https://news.google.com/rss/articles/CBMiqAFBVV95cUxQQVdzV0p5NTVtdlM5bV9fZldLVGR4NnQ5ZzZ5WWVlUWg5M1BvYk1VbkNxczBuYWV1TUpsUFA4UlVUUWtkaE0xSGs0YklsXzRFM01fZEVNQ1EtcTVFblJvUExucDNJVlBYYWFSSXhjdHpndF9kRWFpbDRuT0JSVlkwSVROcnNmazRDSVJOZWpFODJGNnl6X0R1c0Y4TFVibkhHRThOS25WWDc?oc=5) |
| `xai-tn-unnamed` | [Mayor, MLGW push xAI to complete water recycling facility](https://news.google.com/rss/articles/CBMingFBVV95cUxOMFpqVm9RZ3ZvNG9vaHVPTDAyY29WSHJnd1BWZkRiVlFVNEUyclRsLVlaTDFLQW03d213UmJZTnNCSGRQSTJfUjM3SHVKakJrd2dIZ0FyVWpiTGQ3SG9GLWxCbXJkVFluX3dOakpxeWIwQ3I0YmdmVDRBUTZuVENBX3QyblozSGY3RmhzbklpU1FiTFY5MUlnUkhteGF3Z9IBowFBVV95cUxNM0t6amgxSVJJOTF5WWVRWUtsZUVMdnlwVGVjR01WbFdkT1IzVEVRYzdjWkxubW9BckdObTJnaHR1UGJfVWhCR25ZdDducUQ2bU5zSWp1dWdJYnhpQlVFMzBrMzZsQWdtQVdqWmt3Rzk5RWJjeWw1MTdTMnJURzdyU3pfRTRfam9nUTA2dGlrUGFJLTUwMHd4LUdLVW92LS1VQ213?oc=5) |

## Places with several detected records (64 places, 262 records)

Different companies in one city can be different projects; records without a company in the same place usually are not (matching rule (e) needs 40% title overlap within 60 days). Merge with `merge` overrides.

| Place | Records | Without a company |
|---|---|---|
| Atlanta, Georgia | 17 | 11 |
| Detroit, Michigan | 13 | 9 |
| Kansas City, Missouri | 12 | 11 |
| Indianapolis, Indiana | 10 | 7 |
| Port Washington, Wisconsin | 10 | 10 |
| Dallas, Texas | 9 | 4 |
| Chicago, Illinois | 9 | 6 |
| Charlotte, North Carolina | 8 | 4 |
| New Albany, Ohio | 7 | 4 |
| Columbus, Ohio | 7 | 7 |
| Fort Worth, Texas | 7 | 7 |
| Austin, Texas | 6 | 3 |
| Fargo, North Dakota | 5 | 4 |
| Little Rock, Arkansas | 5 | 3 |
| Seattle, Washington | 5 | 2 |
| St. Louis, Missouri | 4 | 3 |
| Memphis, Tennessee | 4 | 2 |
| Reno, Nevada | 4 | 1 |
| Phoenix, Arizona | 4 | 3 |
| Cleveland, Ohio | 4 | 4 |
| El Paso, Texas | 4 | 4 |
| San Antonio, Texas | 4 | 3 |
| Houston, Texas | 3 | 2 |
| Frederick, Maryland | 3 | 2 |
| Tulsa, Oklahoma | 3 | 1 |
| Northern Virginia, Virginia | 3 | 1 |
| Richmond, Virginia | 3 | 0 |
| Louisville, Kentucky | 3 | 1 |
| Cheyenne, Wyoming | 3 | 1 |
| San Jose, California | 3 | 2 |
| Bessemer, Alabama | 3 | 2 |
| Cedar Rapids, Iowa | 3 | 2 |
| Coweta County, Georgia | 3 | 3 |
| Troup County, Georgia | 3 | 3 |
| Bartow County, Georgia | 3 | 3 |
| Boise, Idaho | 3 | 3 |
| Dauphin County, Pennsylvania | 3 | 3 |
| Denver, Colorado | 3 | 3 |
| Des Moines, Iowa | 3 | 3 |
| Nashville, Tennessee | 3 | 3 |

## Umbrellas next to a named record (62)

The umbrella was created after the named site, so it was not folded in automatically.

| Umbrella | Named records, same company and state |
|---|---|
| `aligned-tx-unnamed` | `aligned-dallas-tx-2025` |
| `apple-nc-unnamed` | `apple-maiden`, `apple-charlotte-nc-2025`, `apple-raleigh-nc-2025` |
| `applied-digital-la-unnamed` | `applied-digital-rapides-parish-la-2026` |
| `applied-digital-nd-unnamed` | `polaris-forge-1` |
| `aws-ga-unnamed` | `amazon-georgia`, `aws-atlanta-ga-2024` |
| `aws-in-unnamed` | `project-rainier`, `aws-posey-county-in-2026` |
| `aws-md-unnamed` | `aws-baltimore-md-2026`, `aws-calvert-county-md-2026`, `aws-frederick-md-2025` |
| `aws-mo-unnamed` | `aws-montgomery-county-mo-2026`, `aws-st-louis-mo-2026` |
| `aws-ms-unnamed` | `aws-mississippi` |
| `aws-nc-unnamed` | `aws-richmond-county` |
| `aws-oh-unnamed` | `aws-central-ohio` |
| `aws-or-unnamed` | `aws-boardman` |
| `aws-pa-unnamed` | `aws-pennsylvania`, `aws-bucks-county-pa-2025`, `aws-indiana-county-pa-2026` |
| `aws-va-unnamed` | `data-center-alley` |
| `aws-wa-unnamed` | `aws-seattle-wa-2026`, `aws-walla-walla-county-wa-2026` |
| `coreweave-nd-unnamed` | `polaris-forge-1` |
| `coreweave-pa-unnamed` | `coreweave-lancaster` |
| `crusoe-tx-unnamed` | `stargate-abilene` |
| `crusoe-wy-unnamed` | `crusoe-cheyenne` |
| `digital-realty-tx-unnamed` | `digital-realty-dallas-tx-2025` |
| `google-ar-unnamed` | `google-west-memphis`, `google-little-rock-ar-2026` |
| `google-ia-unnamed` | `google-council-bluffs` |
| `google-in-unnamed` | `google-fort-wayne`, `google-indianapolis-in-2025` |
| `google-mi-unnamed` | `google-detroit-mi-2026`, `google-van-buren-township-mi-2026`, `google-wayne-county-mi-2026` |
| `google-nc-unnamed` | `google-charlotte-nc-2024`, `google-lenoir-nc-2026` |
| `google-ne-unnamed` | `google-papillion` |
| `google-ok-unnamed` | `google-oklahoma` |
| `google-tx-unnamed` | `google-midlothian`, `google-austin-tx-2026` |
| `google-va-unnamed` | `data-center-alley`, `google-botetourt-county-va-2026`, `google-roanoke-county-va-2026` |
| `google-wy-unnamed` | `google-laramie-county-wy-2026` |
| `meta-al-unnamed` | `meta-huntsville-al-2026` |
| `meta-in-unnamed` | `meta-new-carlisle-in-2025` |
| `meta-la-unnamed` | `hyperion` |
| `meta-mo-unnamed` | `meta-kansas-city-mo-2025` |
| `meta-nm-unnamed` | `meta-los-lunas` |
| `meta-oh-unnamed` | `prometheus`, `meta-columbus-oh-2025` |
| `meta-or-unnamed` | `meta-prineville` |
| `meta-tn-unnamed` | `meta-memphis-tn-2024` |
| `meta-tx-unnamed` | `meta-el-paso`, `meta-fort-worth` |
| `microsoft-ga-unnamed` | `fairwater-atlanta` |
| `microsoft-ia-unnamed` | `microsoft-west-des-moines` |
| `microsoft-nc-unnamed` | `microsoft-person-county-nc-2026` |
| `microsoft-oh-unnamed` | `microsoft-columbus-oh-2024`, `microsoft-new-albany-oh-2024` |
| `microsoft-tx-unnamed` | `microsoft-san-antonio` |
| `microsoft-wa-unnamed` | `microsoft-quincy` |
| `microsoft-wi-unnamed` | `fairwater` |
| `openai-ga-unnamed` | `openai-atlanta-ga-2026`, `openai-effingham-county-ga-2026` |
| `openai-mi-unnamed` | `oracle-detroit-mi-2026` |
| `openai-nm-unnamed` | `stargate-do-a-ana-county` |
| `openai-oh-unnamed` | `stargate-lordstown` |
| `openai-tx-unnamed` | `stargate-abilene`, `stargate-milam-county` |
| `oracle-mi-unnamed` | `stargate-michigan`, `oracle-detroit-mi-2026` |
| `oracle-tx-unnamed` | `stargate-abilene` |
| `oracle-wi-unnamed` | `stargate-port-washington-lighthouse` |
| `qts-ga-unnamed` | `qts-fayetteville` |
| `qts-ia-unnamed` | `qts-cedar-rapids-ia-2025` |
| `qts-va-unnamed` | `qts-richmond-va-2026` |
| `skybox-tx-unnamed` | `skybox-round-rock-tx-2025` |
| `softbank-oh-unnamed` | `stargate-lordstown` |
| `vantage-tx-unnamed` | `frontier` |
| `vantage-va-unnamed` | `vantage-stafford-county-va-2025` |
| `xai-tn-unnamed` | `colossus`, `colossus-2` |

## Records to review (5)

Each received headlines naming different companies with nothing in common, which usually means two projects were merged.

| Record | Companies | Example headlines |
|---|---|---|
| `meta-tx-unnamed` | Meta, OpenAI, Oracle | Meta: Meta unveils plans for $1.5bn AI data centre in Texas / OpenAI, Oracle: Oracle and OpenAI drop Texas data center expansion plan, Bloomberg News reports |
| `openai-tx-unnamed` | Crusoe, OpenAI, Vantage | Crusoe, OpenAI: Watch Crusoe Enters Second Phase of Building an OpenAI Texas Data Center / Vantage: Vantage Data Centers breaks ground on data center campus in Texas |
| `site-port-washington-wi-2025-8` | OpenAI, Oracle, SoftBank, Vantage | Vantage: $15 billion Vantage data center breaks ground in Port Washington / OpenAI, Oracle, SoftBank: $15B Stargate data center breaks ground in Wisconsin |
| `stargate-abilene` | Crusoe, Microsoft, OpenAI, Oracle, SoftBank | OpenAI, Oracle, SoftBank: Stargate's first data center is underway in Texas. Public filings show how much it will cost to build. / Crusoe: Crusoe expands Abilene AI campus to 1.2 GW |
| `stargate-port-washington-lighthouse` | OpenAI, Oracle, SoftBank, Vantage | Vantage: Vantage identified as operator for Port Washington's proposed 3.5 gigawatt data center campus / OpenAI, Oracle: Oracle, OpenAI to Build $15 Billion Data Center Site in Wisconsin |
