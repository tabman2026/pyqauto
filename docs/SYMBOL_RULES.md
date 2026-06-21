# Symbol Rules

Supported symbol formats:

- Six digits, such as `000001`, `399001`, or `600000`.
- Six digits plus `.SH`, `.SZ`, or `.BJ`, such as `600000.SH`, `000001.SZ`,
  or `430017.BJ`.

Bare prefixes are mapped as follows:

| Prefix | pytdx market |
|---|---|
| `0`, `3` | Shenzhen (`0`) |
| `5`, `6`, `9` | Shanghai (`1`) |
| `4`, `8` | Beijing (`0` adapter compatibility market, standardized as `.BJ`) |

Unsupported formats raise `UnsupportedSymbolError` with code
`UNSUPPORTED_SYMBOL`.
