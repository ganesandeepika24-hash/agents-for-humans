"""
Tool: check_web_portal

Scrapes a hobby-class registration page for status and pricing info.
Reads structured data-* attributes (not prose text) for reliability.
Always returns a valid RegistrationStatus, even on failure — degrades
gracefully rather than raising, so the agent can reason about "couldn't
check this" as a normal outcome.
"""

from datetime import date

import requests
from bs4 import BeautifulSoup
from strands import tool

from .interfaces import CheckWebPortalInput, ClassOffer, RegistrationStatus


@tool
def check_web_portal(input: CheckWebPortalInput, as_of_date: date | None = None) -> RegistrationStatus:
    today = as_of_date or date.today()

    try:
        response = requests.get(input.url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        status_el = soup.find(id="registration-status")
        if status_el is None:
            raise ValueError("registration-status element not found on page")
        registration_open = status_el.get("data-status") == "open"

        early_bird_el = soup.find(id="early-bird")
        early_bird_deadline = None
        days_until_deadline = None
        if early_bird_el is not None and early_bird_el.get("data-deadline"):
            early_bird_deadline = date.fromisoformat(early_bird_el["data-deadline"])
            days_until_deadline = (early_bird_deadline - today).days

        classes = []
        for el in soup.find_all(class_="class-item"):
            standard_price = float(el.get("data-price-gbp", 0))
            early_bird_price = float(el.get("data-early-bird-price-gbp", standard_price))
            classes.append(ClassOffer(
                name=el.get("data-name", "Unknown class"),
                standard_price_gbp=standard_price,
                early_bird_price_gbp=early_bird_price,
                savings_gbp=standard_price - early_bird_price,
            ))

        return RegistrationStatus(
            scrape_successful=True,
            error_message=None,
            registration_open=registration_open,
            early_bird_deadline=early_bird_deadline,
            days_until_deadline=days_until_deadline,
            classes=classes,
        )

    except Exception as e:
        return RegistrationStatus(
            scrape_successful=False,
            error_message=str(e),
            registration_open=None,
            early_bird_deadline=None,
            days_until_deadline=None,
            classes=[],
        )
