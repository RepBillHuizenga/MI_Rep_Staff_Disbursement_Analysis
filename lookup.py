import pickle
import random
import re
import urllib
import os

import requests
import us
from cached_property import cached_property
from nameparser import HumanName

rep_re = re.compile(
    r'<a href="/congressorg/mlm/congressorg/bio/\?id=(?P<id>[\d]+)\&lvl=(?P<lvl>[\w])\&chamber=(?P<chamber_short>[\w])">(?P<representative>[^<]+)</a></span> <span class="cwsubnormal">\((?P<party>[\w])-(?P<state_abbr>[\w]+)(?P<district>[\d ]+)?'
)
bio_re = re.compile(
    "<!-- START BACKGROUND INFO -->(.*)<!-- END BACKGROUND INFO -->", flags=re.DOTALL
)
bio_data_re = re.compile(
    r'<span class="cwsubbold">(?P<bio_key>[^:]+)[: ]*</span>[\s]*<span class="cwsubnormal">\s*(?P<bio_value>[^<]+)'
)
staffer_re = re.compile(
    r'<span class="cwsubbold">(?P<position>[^:]+)[: ]*</span>[\s]*<span class="cwsubnormal">(?P<name>[^<]+)'
)


class Person:
    @cached_property
    def useragent(self):
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0"

    @cached_property
    def session(self):
        s = requests.Session()
        s.headers = {
            "User-Agent": self.useragent,
            "referer": "http://www.congress.org/congressorg/mlm/congressorg/officials/membersearch/",
        }
        return s

    def get(self, url):
        r = self.session.get(url)
        # Keep for debugging.
        self._r = r
        assert r.status_code == 200
        return r.text

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def first_name(self):
        return self._name["first"]

    @property
    def last_name(self):
        return self._name["last"]

    def __eq__(self, other):
        if isinstance(other, str):
            other = HumanName(other)
            return self._name == other._name
        if isinstance(other, HumanName):
            return self._name == other
        raise Exception(f"Unknown Comparison Type: {type(other)}")


class Congressman(Person):
    def __init__(self, **match_dict):
        for key, value in match_dict.items():
            # Strip whitespace, periods and colons.
            value_ = value.strip(" .:")
            # https://stackoverflow.com/a/2077944
            value_ = " ".join(value_.split(None))
            if len(value_) > 0 and key == "district":
                value_ = int(value_)
            setattr(self, key, value_)

        # HumanName parsing of the representative.
        self._name = HumanName(self.representative)

    def __repr__(self):
        if self.chamber_short == "H":
            return f"Rep<{self.first_name} {self.last_name} ({self.party}), {self.state_abbr}-{self.district}>"
        if self.chamber_short == "S":
            return f"Sen<{self.first_name} {self.last_name} ({self.party}, {self.state_abbr})>"

    @property
    def bio_url(self):
        return f"http://www.congress.org/congressorg/mlm/congressorg/bio/?id={self.id}"

    @property
    def staff_url(self):
        return f"http://www.congress.org/congressorg/mlm/congressorg/bio/staff/?id={self.id}"

    @cached_property
    def bio(self):
        bio = bio_data_re.findall(self.bio_text)
        bio_data = dict()
        for key, value in bio:
            if key == "Marital Status":
                status = value.split(None)
                if len(status) == 1:
                    bio_data["Marital Status"] = status[0]
                    bio_data["Spouse"] = None
                if len(status) == 2:
                    bio_data["Marital Status"] = status[0]
                    bio_data["Spouse"] = status[1].strip("()")
                continue
            bio_data[key] = value.strip()
            key2 = key.replace(" ", "_").replace(".", "").lower()
        return bio_data

    @cached_property
    def staffers(self):
        staffer_data = dict()
        for key, value in staffer_re.findall(self.staffer_text):
            if key in ["Fax", "Phone", "Room", "Birthdate", "Birthplace"]:
                setattr(self, key.lower(), value.strip())
                continue
            staffer_data[key] = str(HumanName(value))

            key2 = key.replace(" ", "_").replace(".", "").lower()
            # staffer_data[key2] = key2
        return staffer_data

    @cached_property
    def staffers2(self):
        staffer_data = dict()
        for key, value in self.staffers.items():
            if value not in staffer_data:
                staffer_data[value] = list()
            staffer_data[value].append(key)
        return staffer_data

    @cached_property
    def staffer_text(self):
        return self.get(self.staff_url)

    @cached_property
    def bio_text(self):
        return self.get(self.bio_url)

    @cached_property
    def state(self):
        return us.states.lookup(self.state_abbr)

    @cached_property
    def chamber(self):
        if self.chamber_short == "H":
            return "House"
        if self.chamber_short == "S":
            return "Senate"

    @cached_property
    def democrat(self):
        return self.party == "D"

    @cached_property
    def republican(self):
        return self.party == "R"

    @cached_property
    def independent(self):
        return self.party == "I"

    @cached_property
    def house(self):
        return self.chamber_short == "H"

    @cached_property
    def senate(self):
        return self.chamber_short == "S"

    @cached_property
    def dict(self):
        return self.as_dict()

    def as_dict(self):
        d = dict()
        for field in dir(self):
            if field == "dict":
                continue
            if field.startswith("_"):
                continue
            if field.endswith("_text"):
                continue
            attr = getattr(self, field)
            if isinstance(attr, (bool, str)):
                d[field] = attr
                continue
        return d

    def __lt__(self, other):
        assert isinstance(other, type(self))
        if self.state == other.state:
            if self.chamber_short == other.chamber_short:
                if self.chamber_short == "S":
                    return self.last_name < other.last_name
                elif self.chamber_short == "H":
                    return self.district < other.district
            else:
                return self.chamber_short < other.chamber_short
        else:
            return self.state_abbr < other.state_abbr


def savepoint(data=None, data_file="congressmen.pickle"):
    if data is not None:
        with open(data_file, "wb") as pickling_on:
            pickle.dump(data, pickling_on)
        del data
    with open(data_file, "rb") as pickle_off:
        return pickle.load(pickle_off)


def load_reps():
    s = requests.Session()
    s.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0",
        "referer": "http://www.congress.org/congressorg/mlm/congressorg/officials/membersearch/",
    }
    member_url = (
        "http://www.congress.org/congressorg/mlm/congressorg/officials/membersearch/"
    )
    r = s.get(member_url)
    reps = list()
    for match in rep_re.findall(r.text):
        tmp = dict()
        for named_group, idx in rep_re.groupindex.items():
            tmp[named_group] = match[idx - 1]
        reps.append(Congressman(**tmp))
    return reps

if __name__ == "__main__":
    if os.path.exists("congressmen.pickle"):
        reps = savepoint()
    else:
        reps = load_reps()
    reps.sort()
    for rep in reps:
        print(f"{rep}")
        for staffer, positions in rep.staffers2.items():
            print(f"\t{staffer}:")
            for position in positions:
                print(f"\t\t{position}")
                
    savepoint(reps)
