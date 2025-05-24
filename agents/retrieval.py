import json
import faiss # type: ignore
import numpy as np
from sentence_transformers import SentenceTransformer # type: ignore
from typing import List, Dict
from models.schemas import ProceduresDataSchema, ProcedureSchema 
from pathlib import Path
from langdetect import detect, DetectorFactory # type: ignore
from translate import Translator as SyncTranslator # type: ignore

# Ensure consistent language detection results
DetectorFactory.seed = 0

class RetrievalAgent:
    def __init__(self, procedures_path: str):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.translator = SyncTranslator(to_lang="fr")
        self.procedures_file_path = Path(procedures_path)
        if not self.procedures_file_path.is_absolute():
            self.procedures_file_path = Path(__file__).resolve().parent.parent.parent / "data" / self.procedures_file_path.name
        if not self.procedures_file_path.exists():
            raise FileNotFoundError(f"Procedures JSON file not found at: {self.procedures_file_path}")
        self.procedures_data = self._load_procedures(str(self.procedures_file_path))
        self.index = None
        self.procedure_objects = []
        self._build_index()

    def _load_procedures(self, path: str) -> ProceduresDataSchema:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ProceduresDataSchema(**data)

    def _build_index(self):
        texts = []
        self.procedure_objects = []
        for proc in self.procedures_data.procedures:
            text = f"Procedure: {proc.procedure}. Remarks: {' '.join(proc.remarks)}. Required documents: {str(proc.documents_required)}"
            texts.append(text)
            self.procedure_objects.append(proc)
        if not texts:
            print("No procedures found to build index.")
            self.index = None
            return
        embeddings = self.model.encode(texts, show_progress_bar=True)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        normalized_embeddings = embeddings.astype('float32').copy()
        faiss.normalize_L2(normalized_embeddings)
        self.index.add(normalized_embeddings)
        print(f"Built FAISS index with {len(texts)} procedures.")

    def _translate_to_french(self, query: str) -> str:
        """
        Translate the input query to French using synchronous libraries.
        If translation fails, return the original query.
        """
        try:
            # Detect language using langdetect
            source_lang = detect(query)
            print(f"Detected language: {source_lang}")
            
            if source_lang == 'fr':
                print("Query is already in French.")
                return query
            
            # Translate using synchronous translator
            translator = SyncTranslator(from_lang=source_lang, to_lang="fr")
            translated_text = translator.translate(query)
            print(f"Original query: {query}")
            print(f"Translated query: {translated_text}")
            return translated_text
            
        except Exception as e:
            print(f"Translation failed: {e}")
            print("Using original query for search.")
            return query

    def search_procedures(self, query: str, top_k: int = 3) -> List[ProcedureSchema]:
        if not self.index or self.index.ntotal == 0:
            print("FAISS index is not built or is empty.")
            return []
        
        # Translate query to French before semantic search
        french_query = self._translate_to_french(query)
        
        query_embedding = self.model.encode([french_query])
        normalized_query_embedding = query_embedding.astype('float32').copy()
        faiss.normalize_L2(normalized_query_embedding)
        scores, indices = self.index.search(normalized_query_embedding, top_k)
        results = []
        if indices.size > 0:
            for i, idx in enumerate(indices[0]):
                if idx == -1:
                    continue
                if scores[0][i] > 0.3:
                     results.append(self.procedure_objects[idx])
        return results