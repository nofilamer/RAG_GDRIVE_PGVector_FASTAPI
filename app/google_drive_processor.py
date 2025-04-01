import logging
import uuid
from datetime import datetime

import pandas as pd
from database.vector_store import VectorStore
from services.google_drive import GoogleDriveService
from services.synthesizer import Synthesizer
from timescale_vector.client import uuid_from_time


class GoogleDriveProcessor:
    """Process files from Google Drive, extract text, and store embeddings."""
    
    def __init__(self):
        """Initialize Google Drive processor with necessary services."""
        self.drive_service = GoogleDriveService()
        self.vector_store = VectorStore()
        
    def setup_database(self):
        """Create necessary database tables and indexes."""
        logging.info("Setting up database tables and indexes...")
        try:
            self.vector_store.create_tables()
            logging.info("Tables created successfully")
        except Exception as e:
            logging.info(f"Tables may already exist: {e}")
            
        try:
            self.vector_store.create_index()
            logging.info("Index created successfully")
        except Exception as e:
            logging.info(f"Index may already exist: {e}")
            
        logging.info("Database setup complete")
        
    def process_file(self, file_name: str):
        """
        Process a file from Google Drive.
        
        Args:
            file_name: The name of the file to process.
            
        Returns:
            bool: True if the file was successfully processed, False otherwise.
        """
        # Search for the file in Google Drive
        file_id = self.drive_service.search_file(file_name)
        
        if not file_id:
            logging.error(f"File '{file_name}' not found in Google Drive")
            return False
        
        # Download the file
        name, mime_type, content = self.drive_service.download_file(file_id)
        logging.info(f"Downloaded file: {name} ({mime_type})")
        
        # Extract text from the file
        text_content = self.drive_service.extract_text_from_file(file_id, mime_type, content)
        
        if not text_content:
            logging.error(f"Could not extract text from file: {name}")
            return False
        
        # Split the text into chunks (simple implementation)
        chunks = self._chunk_text(text_content)
        
        # Process each chunk and store in the database
        self._store_chunks(chunks, name, file_id)
        
        logging.info(f"Successfully processed file: {name}")
        return True
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100):
        """
        Split text into overlapping chunks.
        
        Args:
            text: The text to split.
            chunk_size: The maximum size of each chunk.
            overlap: The overlap between chunks.
            
        Returns:
            List of text chunks.
        """
        chunks = []
        
        if len(text) <= chunk_size:
            chunks.append(text)
        else:
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                
                # If this is not the first chunk and not the last chunk of the text
                if start > 0 and end < len(text):
                    # Adjust start to include overlap
                    start = start - overlap
                
                chunks.append(text[start:end])
                start = end
        
        return chunks
    
    def _store_chunks(self, chunks: list, file_name: str, file_id: str):
        """
        Store text chunks as embeddings in the database.
        
        Args:
            chunks: List of text chunks.
            file_name: The name of the source file.
            file_id: The Google Drive ID of the source file.
        """
        records = []
        
        for i, chunk in enumerate(chunks):
            # Generate embedding for the chunk
            embedding = self.vector_store.get_embedding(chunk)
            
            # Create record
            record = {
                "id": str(uuid_from_time(datetime.now())),
                "metadata": {
                    "source": "google_drive",
                    "file_name": file_name,
                    "file_id": file_id,
                    "chunk_index": i,
                    "created_at": datetime.now().isoformat(),
                },
                "contents": chunk,
                "embedding": embedding,
            }
            
            records.append(record)
        
        # Convert records to DataFrame and upsert to database
        df = pd.DataFrame(records)
        self.vector_store.upsert(df)
        logging.info(f"Stored {len(chunks)} chunks from {file_name}")
    
    def search_documents(self, query: str, limit: int = 5):
        """
        Search for documents matching the query.
        
        Args:
            query: The search query.
            limit: Maximum number of results to return.
            
        Returns:
            The synthesized response.
        """
        # Search for relevant chunks
        results = self.vector_store.search(query, limit=limit)
        
        # Generate a response
        response = Synthesizer.generate_response(question=query, context=results)
        
        return response


def main():
    """Main function to run the Google Drive processor."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    processor = GoogleDriveProcessor()
    
    # Set up the database on first run
    processor.setup_database()
    
    while True:
        print("\n===== Google Drive Document Processor =====")
        print("1. Process a file from Google Drive")
        print("2. Ask a question about your documents")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            file_name = input("Enter the file name to search for in Google Drive: ")
            if processor.process_file(file_name):
                print(f"Successfully processed file: {file_name}")
            else:
                print(f"Failed to process file: {file_name}")
                
        elif choice == "2":
            query = input("Enter your question: ")
            response = processor.search_documents(query)
            
            print(f"\nAnswer: {response.answer}")
            print("\nThought process:")
            for thought in response.thought_process:
                print(f"- {thought}")
            print(f"\nContext: {'Sufficient' if response.enough_context else 'Insufficient'}")
            
        elif choice == "3":
            print("Exiting...")
            break
            
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()