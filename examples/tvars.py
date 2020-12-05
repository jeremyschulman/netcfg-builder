"""
This file contains the primary function to create the device specific variables that will
be passed to the Jinja2 rendering process.
"""

import asyncio
from httpx import Response

from netcfg_builder.netbox import NetboxClient


def get_template_variables(hostname: str) -> dict:
    """
    This function uses the Netbox device record information to then obtain the other
    required template variables.  Presently these include:

        hostname: str
            The device hostname

        site: str
            The device site slug

        ASN: str
            The device ASN values or empty-string

        INTF_DESC: dict
            key: str - interface name
            value: str - interface description or empty-string

        INTF_IPADDR: dict
            key: str - interface name
            value: str - the interface IP address with prefix, "1.1.1.1/30" for exmaple.

        <context-vars>: dict
            If the device contains any context variables stored within Netbox,
            they are included "as-is".  This includes both the heirarchal and local
            dictionaries from `nb_dev`.

    Parameters
    ----------
    hostname: str
        The name of the device

    Returns
    -------
    Dictionary, as described.
    """
    looprun = asyncio.get_event_loop().run_until_complete

    nb = NetboxClient(timeout=60)
    nb_dev = looprun(nb.fetch_device(hostname))

    # setup API params to retrieve only those items specific to this device.
    # the APIs used share the same parameters :-)

    params = dict(device_id=nb_dev["id"], limit=0)

    res_intfs, res_ipaddrs, res_site = looprun(
        asyncio.gather(
            nb.get("/dcim/interfaces", params=params),
            nb.get("/ipam/ip-addresses", params=params),
            nb.get(f"/dcim/sites/{nb_dev['site']['id']}"),
        )
    )

    rp_ipaddr = None

    if hostname.endswith("rs21"):
        # need to fetch rs22 loopback0 IP address
        res: Response = looprun(
            nb.get(
                "/ipam/ip-addresses",
                params={"interface": "loopback0", "device": hostname[0:3] + "rs22"},
            )
        )

        res.raise_for_status()
        body = res.json()
        if body["count"] != 1:
            raise RuntimeError("RS22 loopback0 IP not found")

        rp_ipaddr = body["results"][0]["address"]

    looprun(nb.aclose())

    intf_recs = res_intfs.json()["results"]
    ipaddr_recs = res_ipaddrs.json()["results"]
    site_rec = res_site.json()

    tvars = dict(
        hostname=nb_dev["name"],
        site=nb_dev["site"]["slug"],
        ASN=site_rec["asn"],
        INTF_DESC={rec["name"]: rec["description"] for rec in intf_recs},
        INTF_IPADDR={rec["interface"]["name"]: rec["address"] for rec in ipaddr_recs},
    )

    if not rp_ipaddr:
        rp_ipaddr = tvars["INTF_IPADDR"]["loopback0"]

    tvars["pim_rp_address"] = rp_ipaddr.split("/")[0]

    if (rcd := nb_dev["config_context"]) is not None:
        tvars.update(rcd)

    if (lcd := nb_dev["local_context_data"]) is not None:
        tvars.update(lcd)

    return tvars
