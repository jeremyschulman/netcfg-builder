# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from pathlib import Path
from functools import cached_property
import re

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import jinja2


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


class RelativeEnvironment(jinja2.Environment):
    """
    The RelativeEnvironment allows the Developer to create Jinja2 templates that
    use the include directive using relative paths, for example:

        {% include "../thisdir/otherfile.j2" %}
    """

    @cached_property
    def _templatedir(self) -> Path:
        return self.loader.searchpath[0]

    def join_path(self, template, parent):  # noqa
        path = (
            self._templatedir.joinpath(Path(parent).parent).joinpath(template).resolve()
        )
        r_path = path.relative_to(self._templatedir)
        return str(r_path)

    def handle_exception(self, source=None):
        """
        Intercept the exception to handle the use of RuntimeError if it was the
        cause of the exception.  This will add the filename and lineno to the
        RuntimeError message.

        If not, perform the default hanlding.
        """
        from jinja2.debug import rewrite_traceback_stack

        exc = rewrite_traceback_stack()

        if isinstance(exc, RuntimeError):
            tb = exc.__traceback__
            filename = tb.tb_frame.f_code.co_filename
            raise RuntimeError(f"{filename}:{tb.tb_lineno}: {exc.args[0]}")

        raise exc


def _gfunc_raise(msg):
    """ used to allow a Jinja2 file to raise an exception """
    raise RuntimeError(msg)


def iface_key(if_name):
    if_num = list(map(int, re.findall(r"\d+", if_name)))
    if_num.insert(0, re.search(r"([^\d])+", if_name).group(0))
    return if_num


def _filter_ifaces_numeric(if_list):
    return sorted(if_list, key=iface_key)


def render(template_fp: Path, **tvars) -> str:
    """
    The `render` function is use to template build (render) the given Jinja2
    template file using the provided template variables.

    Parameters
    ----------
    template_fp: Path
        The template file path instnace.

    tvars: dict
        The collection of variables that will be passed AS-IS to the Jinja2
        template.

    Returns
    -------
    The rendered text string.
    """

    env = RelativeEnvironment(
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        loader=jinja2.FileSystemLoader(template_fp.parent.absolute()),
    )

    env.globals["raise"] = _gfunc_raise

    env.tests["None"] = lambda pred: pred is None
    env.tests["contains"] = lambda val, pred: val in pred
    env.tests["startswith"] = lambda val, pred: val.startswith(pred)

    env.filters["ifaces_numeric"] = _filter_ifaces_numeric
    template = env.get_template(template_fp.name)
    return template.render(tvars)
