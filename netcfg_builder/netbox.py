from typing import Optional, Dict, List
import asyncio
from os import environ
from operator import itemgetter
from itertools import chain


from httpx import AsyncClient, Response
from tenacity import retry, wait_exponential


class NetboxClient(AsyncClient):
    ENV_VARS = ["NETBOX_ADDR", "NETBOX_TOKEN"]
    DEFAULT_PAGE_SZ = 100

    def __init__(self, **kwargs):
        try:
            url, token = itemgetter(*NetboxClient.ENV_VARS)(environ)
        except KeyError as exc:
            raise RuntimeError(f"Missing environment variable: {exc.args[0]}")

        super().__init__(
            base_url=f"{url}/api",
            headers=dict(Authorization=f"Token {token}"),
            verify=False,
            **kwargs,
        )

    async def request(self, *vargs, **kwargs) -> Response:
        @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
        async def _do_rqst():
            res = await super(NetboxClient, self).request(*vargs, **kwargs)
            if res.status_code == 429:
                res.raise_for_status()
            return res
        return await _do_rqst()

    async def paginate(
        self, url: str, page_sz: Optional[int] = None, filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Concurrently paginate GET on url for the given page_sz and optional
        Caller filters (Netbox API specific).  Return the list of all page
        results.

        Parameters
        ----------
        url:
            The Netbox API URL endpoint

        page_sz:
            Max number of result items

        filters:
            The Netbox API params filter options.

        Returns
        -------
        List of all Netbox API results from all pages
        """

        # GET the url for limit = 1 record just to determin the total number of
        # items.

        params = filters or {}
        params["limit"] = 1

        res = await self.get(url, params=params)
        res.raise_for_status()
        body = res.json()
        count = body["count"]

        # create a list of tasks to run concurrently to fetch the data in pages.
        # NOTE: that we _MUST_ do a params.copy() to ensure that each task has a
        # unique offset count.  Observed that if copy not used then all tasks have
        # the same (last) value.

        params["limit"] = page_sz or self.DEFAULT_PAGE_SZ
        tasks = list()

        for offset in range(0, count, params["limit"]):
            params["offset"] = offset
            tasks.append(self.get(url, params=params.copy()))

        task_results = await asyncio.gather(*tasks)

        # return the flattened list of results

        return list(
            chain.from_iterable(task_r.json()["results"] for task_r in task_results)
        )

    async def fetch_device(self, hostname):
        res: Response = await self.get("/dcim/devices", params=dict(name=hostname))
        res.raise_for_status()
        body = res.json()

        if body["count"] != 1:
            raise RuntimeError(f"Device {hostname} not found in Netbox.")

        return body["results"][0]
