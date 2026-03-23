"""
Database module for storing analysis history and user feedback
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

class AnalysisDatabase:
    def __init__(self, db_path='analysis_history.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Analysis history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_hash TEXT UNIQUE,
                article_text TEXT,
                article_preview TEXT,
                prediction TEXT,
                confidence REAL,
                real_prob REAL,
                fake_prob REAL,
                red_flag_score REAL,
                model_scores TEXT,
                source_url TEXT,
                source_domain TEXT,
                category TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_hash TEXT,
                user_rating INTEGER,
                correct_label TEXT,
                feedback_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_hash) REFERENCES analysis_history(article_hash)
            )
        ''')
        
        # Source reputation table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_reputation (
                domain TEXT PRIMARY KEY,
                reputation_score REAL,
                total_analyzed INTEGER DEFAULT 0,
                fake_count INTEGER DEFAULT 0,
                real_count INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_analysis(self, article_text: str, prediction: str, confidence: float,
                    real_prob: float, fake_prob: float, red_flag_score: float,
                    model_scores: Dict = None, source_url: str = None,
                    source_domain: str = None, category: str = None) -> str:
        """Add analysis record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create hash for article
        import hashlib
        article_hash = hashlib.md5(article_text.encode()).hexdigest()
        article_preview = article_text[:200]
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO analysis_history 
                (article_hash, article_text, article_preview, prediction, confidence,
                 real_prob, fake_prob, red_flag_score, model_scores, source_url,
                 source_domain, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (article_hash, article_text, article_preview, prediction, confidence,
                  real_prob, fake_prob, red_flag_score, json.dumps(model_scores),
                  source_url, source_domain, category))
            
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Article already exists
        finally:
            conn.close()
        
        return article_hash
    
    def add_feedback(self, article_hash: str, rating: int, correct_label: str = None,
                    feedback_text: str = None):
        """Add user feedback"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_feedback 
            (article_hash, user_rating, correct_label, feedback_text)
            VALUES (?, ?, ?, ?)
        ''', (article_hash, rating, correct_label, feedback_text))
        
        conn.commit()
        conn.close()
    
    def get_history(self, limit: int = 100) -> pd.DataFrame:
        """Get recent analysis history"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT id, article_preview, prediction, confidence, 
                   real_prob, fake_prob, red_flag_score,
                   source_domain, category, timestamp
            FROM analysis_history
            ORDER BY timestamp DESC
            LIMIT ?
        '''
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    
    def get_statistics(self) -> Dict:
        """Get analysis statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total analyses
        cursor.execute('SELECT COUNT(*) FROM analysis_history')
        total = cursor.fetchone()[0]
        
        # Prediction counts
        cursor.execute('''
            SELECT prediction, COUNT(*) 
            FROM analysis_history 
            GROUP BY prediction
        ''')
        pred_counts = dict(cursor.fetchall())
        
        # Average confidence
        cursor.execute('SELECT AVG(confidence) FROM analysis_history')
        avg_conf = cursor.fetchone()[0] or 0
        
        # Top red flags
        cursor.execute('''
            SELECT article_preview, red_flag_score
            FROM analysis_history
            WHERE red_flag_score > 0.5
            ORDER BY red_flag_score DESC
            LIMIT 10
        ''')
        top_flags = cursor.fetchall()
        
        # Category distribution
        cursor.execute('''
            SELECT category, COUNT(*)
            FROM analysis_history
            WHERE category IS NOT NULL
            GROUP BY category
        ''')
        categories = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total': total,
            'predictions': pred_counts,
            'avg_confidence': avg_conf,
            'top_red_flags': top_flags,
            'categories': categories
        }
    
    def get_source_reputation(self, domain: str) -> Optional[Dict]:
        """Get reputation for a source domain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT domain, reputation_score, total_analyzed, fake_count, real_count
            FROM source_reputation
            WHERE domain = ?
        ''', (domain,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'domain': row[0],
                'reputation': row[1],
                'total': row[2],
                'fake_count': row[3],
                'real_count': row[4]
            }
        return None
    
    def update_source_reputation(self, domain: str, is_fake: bool):
        """Update source reputation based on analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current stats
        cursor.execute('''
            SELECT total_analyzed, fake_count, real_count
            FROM source_reputation
            WHERE domain = ?
        ''', (domain,))
        
        row = cursor.fetchone()
        
        if row:
            total, fake, real = row
            total += 1
            if is_fake:
                fake += 1
            else:
                real += 1
        else:
            total = 1
            fake = 1 if is_fake else 0
            real = 0 if is_fake else 1
        
        # Calculate reputation (0-100, higher = more trustworthy)
        reputation = (real / total) * 100 if total > 0 else 50
        
        cursor.execute('''
            INSERT OR REPLACE INTO source_reputation
            (domain, reputation_score, total_analyzed, fake_count, real_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (domain, reputation, total, fake, real, datetime.now()))
        
        conn.commit()
        conn.close()
