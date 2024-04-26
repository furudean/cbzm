# cbzm

cbz merge - merge comic archives

## installation

it is assumed you have python>=3.11 with [pipx](https://github.com/pypa/pipx) installed

```
pipx install cbzm
```

## use

```
cbzm 1.cbz 2.cbz out.cbz
```

`1.cbz`, `2.cbz` etc get merged into a new archive on the last positional
argument, `out.cbz`

| Option                                  | Description                                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `--compress {store,deflate,bzip2,lzma}` | compression method to use for the output archive (default: store)                                      |
| `--slice SLICE`                         | python slice expression for pages to pick from each archive, for example `:-1` to remove the last page |
| `-y`                                    | overwrite output file                                                                                  |
| `--help`                                | show command usage                                                                                     |
