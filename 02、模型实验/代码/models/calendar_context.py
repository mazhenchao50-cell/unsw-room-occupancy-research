"""Independently sourced calendar context for the documented UNSW 2017 window.

Dates are pre-class information. A calendar alert is a review flag, not an
estimated probability or confirmation that a session was cancelled or vacant.
"""
import pandas as pd

WINDOW_START='2017-07-24'
WINDOW_END='2017-10-20'
STATEWIDE_PUBLIC_HOLIDAYS=('2017-10-02',)
SOURCES=(
    'https://www.coursearchive.unsw.edu.au/documents/precool/TABL2751_Business_Taxation_S2_2017.pdf',
    'https://files.parliament.nsw.gov.au/fileapi/ParlFiles/GetArtifact/2017%20Sitting%20calendar.pdf?serverRelativeUrl=%2Ftp%2Ffiles%2F69484%2F2017+Sitting+calendar.pdf',
)
SOURCE_SHA256={
    'UNSW_TABL2751_2017.pdf':'3f52137095e5bec42a70dfc9ac01611cb401391436904744f24e4020f4233933',
    'NSW_Parliament_2017_Calendar.pdf':'c2e111f8f8a32bf35a884a6a8863a37a1267fec5ad9a9384b81eb44f65c8bc49',
}


def review_flag(query):
    dates=pd.to_datetime(query.date,errors='coerce')
    if dates.isna().any() or dates.lt(WINDOW_START).any() or dates.gt(WINDOW_END).any():
        raise ValueError('Calendar context requires a date within the verified UNSW 2017 window')
    # NSW's August bank holiday is NOT a statewide public holiday.
    return dates.dt.strftime('%Y-%m-%d').isin(STATEWIDE_PUBLIC_HOLIDAYS).to_numpy()
