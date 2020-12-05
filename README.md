# Network Config Builder

As a network automation engineer I need to template build network device
configurations.  I want to use Jinja2 as my templating language.  I want to be
able to use the Jinaj `include` directive so that I can include relative
template files. I want the ability to dynamically create variable collections
for each host using native Python, and have a tool that correlates these
variables based on a priority ordering.

This repostory provides such a tool.

```shell
$ netcfg-builder --template <template-file.j2> -e <extra-variables>
```

When `-e <varname>=<value>`, then the variable name `varname` is defined with the value `<value>`.

For example, define a varialbe called `varsdir` that has the value `/usr/local/myvars`.

```shell
$ netcfg-build --template <template-file> -e vardirs=/usr/local/lib/myvars
```

When `<extra-varialbes>` is a `.py` file, that file needs to decorator functions; each
of these functions will be called in priority order.  Priority 0 is first.

For example:

```python
from pathlib import Path
from netcfg_builder.variables import ingest, load_directory

@ingest(0)
def load_variables(tvars: dict, **extras):
    varsdir = Path(extras['varsdir'])
    tvars.update(load_directory(varsdir.joinpath('common')))
    tvars.update(load_directory(varsdir.joinpath(extras['hostname'])))
```

The first parameter, `tvars` to the decordated function is current set of template variables.
The second parameter, `**extras` are any extra variables defined on the command line.

