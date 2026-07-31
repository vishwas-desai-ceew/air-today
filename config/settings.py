from datetime import time

# The CPCB/IMD bulletin is published daily around 18:00 IST. Before this
# cutoff, "today" still refers to yesterday's bulletin data. This was
# previously reimplemented independently in 4 places with 3 different
# (partly wrong) values - this is the single source of truth now.
EFFECTIVE_DATE_CUTOFF = time(17, 57)  # 5:57 PM IST
