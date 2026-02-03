from commons.models import Store, Genre

# Get all genres for mapping
genre_map = {g.name: g for g in Genre.objects.all()}

stores = Store.objects.all()
count = 0

for store in stores:
    # Try exact match first
    # Many stores have "1", "中華" etc.
    if store.genre in genre_map:
        store.genre_master = genre_map[store.genre]
        store.save()
        count += 1
    else:
        # Try partial match or special cases
        # e.g. "中華" match with "中華料理"
        for g_name, g_obj in genre_map.items():
            if store.genre in g_name or g_name in store.genre:
                store.genre_master = g_obj
                store.save()
                count += 1
                break

print(f"Successfully linked {count} stores to genre master.")
