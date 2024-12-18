from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
from typing import List, Optional
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from pymongo.errors import PyMongoError
from fastapi.middleware.cors import CORSMiddleware  # Importer CORSMiddleware
load_dotenv()

#MONGO_URI = os.getenv("MONGO_URI")
#MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
#MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME")
 

MONGO_URI="mongodb://localhost:27017/"
# Connexion à MongoDB
client = MongoClient(MONGO_URI)  # Changez si vous utilisez MongoDB Atlas
# Sélection de la base de données et de la collection
db = client["jobs"]
collection = db["job_posts"]

app = FastAPI()

# Configuration CORS pour autoriser toutes les origines
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permet toutes les origines
    allow_credentials=True,
    allow_methods=["*"],  # Permet toutes les méthodes (GET, POST, etc.)
    allow_headers=["*"],  # Permet tous les headers
)



MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME")


# Pydantic model for the job data
class Job(BaseModel):
    job_title: str = Field(alias='job title')
    company_name: str = Field(alias='company name')
    location: str
    description: str
    links: str
    date: str
    source: str



def get_database():
    client = MongoClient(MONGO_URI)
    #db = client[MONGO_DB_NAME]
    db = client["jobs"]
    return db

def get_collection():
    db = get_database()
    #collection = db[MONGO_COLLECTION_NAME]
    collection = db["job_posts"]
    return collection

# Endpoint to fetch all jobs (unfiltered)
@app.get("/jobs" )# ,response_model=List[Job]
async def read_jobs():
    def clean_description(text):
        return text.rstrip('…').strip()

    try:
        collection = get_collection()
        jobs_cursor = collection.find()
        jobs = list(jobs_cursor)

        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found")
        
        # Transform and clean job data
        transformed_jobs = []
        for job in jobs:
            transformed_job = {
                "id": str(job.get("_id", "")),
                "job_title": job.get("job title", ""),
                "company_name": job.get("company name", ""),
                "location": job.get("location", ""),
                "description": clean_description(job.get("description", "")),
                "links": job.get("links", ""),
                "date": job.get("date", ""),
                "source": job.get("source", "")
            }
            transformed_jobs.append(transformed_job)

        return transformed_jobs

    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
# Endpoint to filter jobs by any field using "find"
@app.get("/jobs/filter")#, response_model=List[Job]
async def filter_jobs(
    job_title: Optional[str] = None,
    company_name: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    date: Optional[str] = None
    ):
    collection = get_collection()
    query = {}

    if job_title:
        query["job_title"] = {"$regex": job_title, "$options": "i"}  # "i" for case-insensitive search
    if company_name:
        query["company_name"] = {"$regex": company_name, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if description:
        query["description"] = {"$regex": description, "$options": "i"}
    if date:
        query["date"] = {"$regex": date, "$options": "i"}

    jobs_cursor = collection.find(query)
    jobs = list(jobs_cursor)
    
    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found matching the criteria")
    
    for job in jobs:
        if "_id" in job:
            job["_id"] = str(job["_id"])
    return jobs



# Endpoint to search using text indexes (for text search on job_title, description)
@app.get("/jobs/search")#, response_model=List[Job]
async def search_jobs(keyword: str):
     collection = get_collection()
     
     if not keyword:
         raise HTTPException(status_code=400, detail="Keyword cannot be empty")

     jobs_cursor = collection.find( { "$text": { "$search": keyword } } )
     jobs = list(jobs_cursor)
     
     if not jobs:
          raise HTTPException(status_code=404, detail="No jobs found matching the keyword")
     
     for job in jobs:
          if "_id" in job:
            job["_id"] = str(job["_id"])
     return jobs


# Create index
@app.on_event("startup")
async def create_text_index():
    collection = get_collection()
    collection.create_index([("job_title", "text"),("description","text")])
    print("Text index created if not present")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)