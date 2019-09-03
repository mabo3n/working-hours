import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SHEET_URL = r'https://docs.google.com/spreadsheets/d/<ID>/edit#gid=0'
BUSINESS_DAY_DEFAULT_TARGET_HOURS = 8.5


def df_from_google_sheet(url):
    csv_export_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    return pd.read_csv(csv_export_url)

def total_hours(timedeltas):
    return timedeltas.map(lambda t: pd.Timedelta(t).total_seconds()/(60*60))



# Read whole sheet data into a dataframe
sheet_data = df_from_google_sheet(SHEET_URL)

# Set 'Data' column as the index
sheet_data['Data'] = pd.to_datetime(sheet_data['Data'], dayfirst=True)
sheet_data.set_index('Data', inplace=True)

# Get target hours override for holidays and alike
target_hours_override = sheet_data['Horas requeridas']

# Get separated dataframes for Start and End times
start_times = sheet_data.filter(regex='^[Ii]n[ií]cio.*$').apply(pd.to_datetime)
end_times = sheet_data.filter(regex='^[Ff]im.*$').apply(pd.to_datetime)

# Standardize dataframes' columns
start_times.columns = end_times.columns = range(start_times.columns.size)

# Get a Series of working time for each day
daily_working_time = (end_times-start_times).agg(np.sum, axis=1)

# Cumulative hours of working time per day
cum_hours_of_working_time = total_hours(daily_working_time.cumsum())

# New Dataframe
performance = pd.DataFrame({ 
    'working_time': daily_working_time,
    'cum_working_hours': cum_hours_of_working_time })

# Set target working hours' default value for each day
performance['target_working_hours'] = 0
performance.loc[performance.index.dayofweek<5, 
                'target_working_hours'] = BUSINESS_DAY_DEFAULT_TARGET_HOURS

# Override target working hours with user specified values (if any)
performance['target_working_hours'].update(target_hours_override)

# Cumulative target working hours
performance['cum_target_working_hours'] = performance['target_working_hours'].cumsum()

# Working/target hours balance 
balance = (performance['cum_working_hours'].tail(1)
            -performance['cum_target_working_hours'].tail(1)).values[0]

### Plotting ###

# Filter the last 7 [or less] days to plot
index_of_last_filled_row = sheet_data.dropna(thresh=4).tail(1).index[0]
last_week_performance = performance.loc[:index_of_last_filled_row].tail(7)

# Get suitable representation for each day -- 'Fri (2019-01-01)'
days = last_week_performance.index.day_name().map(lambda s: s[:3])
days += last_week_performance.index.map(
    lambda date: '\n({})'.format(date.strftime('%d/%m')))

hours_required = last_week_performance['cum_target_working_hours']
hours_worked = last_week_performance['cum_working_hours']

plt.figure(figsize=(9,6))

plt.plot(days, hours_required, 
        'k:', alpha=.5, label='Required')
plt.plot(days, hours_worked, 
        'o', color='#015187', linestyle='-', label='Undertaken')

plt.legend(loc='upper left')
plt.ylabel('Hours')
plt.xlabel('Day')
plt.title('Working hours balance')

ann_balance_color = '#00cc66' if balance >=0 else '#C92A2A'
ann_balance_text = ('    +{}h'.format(round(balance,2)) if balance>0.0 
                    else '    {}h'.format(round(balance,2)))

plt.annotate('', 
            xy=(days[-1], hours_worked[-1]), 
            xycoords='data', 
            xytext=(days[-1], hours_required[-1]), 
            textcoords='data', 
            arrowprops={'arrowstyle': '|-|', 
                        'color':ann_balance_color})

plt.text(x=days[-1],
        y=(hours_required[-1] + hours_worked[-1])*.5,
        s=ann_balance_text,
        fontsize='13',
        color=ann_balance_color)

plt.show()
