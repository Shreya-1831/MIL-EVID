import os

from dotenv import load_dotenv

from app.modules.ingestion.acled_client import ACLEDClient
from app.modules.retrieval.acled_retriever import ACLEDDynamicRetriever


load_dotenv()

client = ACLEDClient(
    username=os.environ["ACLED_USERNAME"],
    password=os.environ["ACLED_PASSWORD"],
)

retriever = ACLEDDynamicRetriever(client)

documents = retriever.retrieve(
    country="India",
    # updated_since="2021-01-01",
    start_date="2026-01-01",
    end_date="2026-09-13",
    limit=20,
)

print("=" * 80)
print("MIL-EVID — ACLED DYNAMIC RETRIEVER TEST")
print("=" * 80)

print(f"\nRetrieved military-relevant documents: {len(documents)}")

for index, document in enumerate(documents, start=1):
    print(f"\n--- Document {index} ---")
    print(f"ID:          {document.id}")
    print(f"Source:      {document.source}")
    print(f"Perspective: {document.perspective}")
    print(f"Title:       {document.title}")
    print(f"Date:        {document.date}")
    print(f"Event type:  {document.metadata.get('event_type')}")
    print(f"Location:    {document.metadata.get('location')}")
    print(f"Fatalities:  {document.metadata.get('fatalities')}")

print("\n" + "=" * 80)
print("ACLED DYNAMIC RETRIEVER TEST COMPLETE")
print("=" * 80)