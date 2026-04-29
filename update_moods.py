import pandas as pd
import pickle

# Load your existing dataframe
with open('df_with_mood.pkl', 'rb') as f:
    df = pickle.load(f)

# Correct the moods for specific songs
# You can add as many songs as you want here
songs_to_fix = {
    'Let Her Go': 'sad',
    'Home': 'sad'
}

for song, correct_mood in songs_to_fix.items():
    df.loc[df['track_name'].str.contains(song, case=False, na=False), 'mood'] = correct_mood

# Save the updated dataframe back to the pickle file
with open('df_with_mood.pkl', 'wb') as f:
    pickle.dump(df, f)

print("Dataset updated successfully!")