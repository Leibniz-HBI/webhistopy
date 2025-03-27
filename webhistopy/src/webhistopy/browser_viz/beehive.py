import plotly
from sklearn.cluster import KMeans
from sklearn.preprocessing import MaxAbsScaler
import polars as pl
import datetime
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import sys
from sklearn.preprocessing import StandardScaler
import numpy as np

def to_default_datetime_format(date_str):

    if isinstance(date_str,str):
        return datetime.strptime(date_str[:20],"%Y-%m-%d %H:%M:%S")
    else:
        return date_str

def get_diff_in_seconds(start_date,end_date):

    diff = to_default_datetime_format(end_date)-to_default_datetime_format(start_date)
    return diff.total_seconds()

def add_day(df):

    df = df.with_columns((pl.col("dt").cast(pl.Utf8).str.slice(0, 10)).alias("day"))
    return df

def add_month(df):

    df = df.with_columns((pl.col("dt").cast(pl.Utf8).str.slice(0, 7)).alias("month"))
    return df

def add_hour(df):

    df = df.with_columns((pl.col("dt").cast(pl.Utf8).str.slice(11,length=2)).alias("hour"))
    return df

def add_minute(df):

    df = df.with_columns((pl.col("dt").cast(pl.Utf8).str.slice(11,length=4)).alias("minute"))
    return df

def add_timedelta():

    pass

def add_is_within(df,main_col="Domain",dt_col="dt",within_secs=604800):

	prev_o = None
	row_count = 0
	rows_nums = []
	dgroups = []
	for o,dt in zip(df[main_col].to_list(),df[dt_col].to_list()):
		rows_nums.append(row_count)
		if o != prev_o:
			i = 0
			dgroups.append(i)
		else:
			if get_diff_in_seconds(prev_dt,dt) < within_secs:
				dgroups.append(i)
			else:
				i+=1
				dgroups.append(i)
		prev_o = o
		prev_dt = dt
		row_count+=1
	
	df = df.with_columns(pl.Series(name=f"with_secs_{within_secs}",values=dgroups))
		
	return df

def create_day_matrix(df,day_col="day",main_col="Domain"):
    
    df = df.select([day_col,main_col]).groupby([main_col,day_col]).count()

    # Calculate total counts per category
    category_totals = df.groupby(day_col).agg(pl.sum('count').alias('category_total'))

    # Join the total counts back to the original DataFrame
    df = df.join(category_totals, on=day_col)

    # Calculate Term Frequency (TF)
    df = df.with_columns((pl.col('count') / pl.col('category_total')).alias('tf'))

    # Calculate Document Frequency (DF)
    entity_category_counts = df.select([
        pl.col('Domain'),
        pl.col(day_col)
    ]).unique()

    df = df.join(
        entity_category_counts.groupby('Domain').agg(pl.count(day_col).alias('df')),
        on='Domain'
    )

    # Calculate Inverse Document Frequency (IDF)
    total_categories = df.select(pl.col(day_col).n_unique())[0, 0]
    df = df.with_columns((np.log(total_categories / pl.col('df'))).alias('idf'))

    # Calculate TF-IDF
    dfg = df.with_columns((pl.col('tf') * pl.col('idf')).alias('tfidf'))

    dfgp = dfg.pivot(index=main_col, columns=day_col, values="tfidf", aggregate_function="sum").fill_null(strategy="zero")
    #print (dfgp)
    #print (df.select([day_col,main_col]).transpose(include_header=True))
    return dfgp

def create_k_means(df,k=4):

    X = df.drop("Domain").to_pandas()
    X = StandardScaler().fit_transform(X)
    km = KMeans(
    n_clusters=k, init='random',
    n_init=10, max_iter=300, 
    tol=1e-04, random_state=0
    )
    y_km = km.fit_predict(X)
    df = df.with_columns(pl.Series(name=f"k_means_label",values=y_km))

    return X, y_km, km, df

def visualize_k_means(X,y_km,km):
    
    # Reduce dimensionality using PCA
    pca = PCA(n_components=2)
    df_reduced = pca.fit_transform(X)

    # Plot the results
    plt.figure(figsize=(10, 7))
    plt.scatter(df_reduced[:, 0], df_reduced[:, 1], c=y_km, s=50, cmap='viridis')

    # Plot the cluster centers
    centers = km.cluster_centers_
    centers_reduced = pca.transform(centers)
    plt.scatter(centers_reduced[:, 0], centers_reduced[:, 1], c='red', s=200, alpha=0.75, marker='x')

    plt.title("K-Means Clustering Visualization with PCA")
    plt.xlabel("Principal Component 1")
    plt.ylabel("Principal Component 2")
    plt.show()

def visualize_beeswarm(df,tcol="day"):

    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns

    data = df.groupby([tcol,"label"]).count()
    data = data.with_columns((np.sqrt(pl.col("count")).cast(pl.Int32)).alias("count")).sort(tcol,descending=False)
    nl_doms = df.groupby(["Domain","label"]).count().sort("count",descending=True).groupby("label").agg((pl.col("Domain"))).with_columns(pl.col("Domain").list.slice(0, 5)).sort("label",descending=False)
    #print (nl_doms)
    #sys.exit()
    df = data.to_pandas()

    # Expand the DataFrame according to the count
    expanded_data = []
    for index, row in df.iterrows():
        for _ in range(row['count']):
            expanded_data.append([row['label'], row[tcol]])

    # Create an expanded DataFrame
    expanded_df = pd.DataFrame(expanded_data, columns=['label', tcol]).sort_values(by="label",ascending=True)
    expanded_df['value'] = 1

    # Create a beeswarm plot
    plt.figure(figsize=(12, 6))
    ax = sns.swarmplot(x=tcol, hue='label', data=expanded_df, palette='Set1', dodge=False)

    plt.title('Beeswarm Plot')
    plt.xlabel('Label')
    plt.ylabel('Markers')
    # Get the handles and labels from the existing legend
    handles, _ = ax.get_legend_handles_labels()

    # Create a custom legend
    #N = 14  # Show every 2nd label
    #ax.set_xticks(range(0, len(expanded_df[tcol]), N))
    #ax.set_xticklabels(expanded_df[tcol][::N])
    # Add the custom legend to the plot
    custom_legend = plt.legend(handles, nl_doms["Domain"].to_list(), title='Colors', loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3)
    #ax.add_artist(custom_legend)

    # Remove the default legend
    #ax.legend_.remove()
    #plt.legend(title='', loc='upper left', labels=nl_doms["Domain"].to_list())
    #sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    #plt.tight_layout()
    plt.tight_layout()
    plt.show()

def main():
    print("starting")
    if len(sys.argv) < 2:
        main_path = "~/Desktop"
        file_name = "test_web_histopy_history.csv"
        file_path = main_path+"/"+file_name
    else:
        filepath = sys.argv[1]
    df = pl.read_csv(file_path,dtypes={"Zeit":pl.Datetime})
    df = df.rename({"Zeit":"dt"})
    df = add_day(df)
    df = add_hour(df)
    df = add_minute(df)
    df = add_month(df)

    n_clusters = 6
    time_level = "day"
    time_level_viz = "day"

    day_matrix = create_day_matrix(df,day_col=time_level)
    X, y_km, km, day_matrix = create_k_means(day_matrix,n_clusters)
    day_matrix_to_map = day_matrix.select(["Domain","k_means_label"]).to_dict(as_series=False)
    df = df.with_columns(pl.col("Domain").map_dict({k:v for k,v in zip(day_matrix_to_map["Domain"],day_matrix_to_map["k_means_label"])}).alias("label"))
    visualize_beeswarm(df,tcol="day")
    

if __name__ == "__main__":
    main()