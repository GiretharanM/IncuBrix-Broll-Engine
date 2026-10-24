from app.adapters.footage.pixabay_adapter import PixabayFootageAdapter

adapter = PixabayFootageAdapter()

queries = [
    "golden retriever playing in a park",
    "golden retriever playing in a park in scenic outdoor environment wide angle",
    "puppies running on grass",
    "puppies running on grass moving smoothly through frame medium distance",
    "dogs running on a beach",
    "dogs running on a beach close-up detail focus crisp lighting",
]

for q in queries:
    res = adapter.search_footage(q, count=5)
    print(f'Query: "{q}" -> {len(res)} hits')
    if res:
        print(f'   First clip ID: {res[0]["id"]}, title: {res[0]["title"][:60]}...')
