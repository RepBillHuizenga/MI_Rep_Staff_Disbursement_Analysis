import glob
import os
import random
import warnings

import IPython.display as display
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import us
from cached_property import cached_property
from nameparser import HumanName

import lookup

warnings.filterwarnings("ignore")
pd.options.display.max_rows = 999
fmt = "${x:,.0f}"
dollar_tick = mtick.StrMethodFormatter(fmt)
