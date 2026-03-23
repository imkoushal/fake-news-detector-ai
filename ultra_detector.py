"""
Hybrid Fake News Detection System
Simplified version without external dependencies
"""
import joblib
import numpy as np
import re
from datetime import datetime

class UltraDetector:
    """
    Fake news detection combining:
    1. ML Model prediction
    2. Linguistic pattern analysis
    3. Simple ensemble fusion
    """
    
    def __init__(self, model_path='models/model.joblib', tfidf_path='models/tfidf.joblib'):
        self.ml_model = None
        self.tfidf = None
        
        # Load ML model if available
        try:
            self.ml_model = joblib.load(model_path)
            self.tfidf = joblib.load(tfidf_path)
            self.ml_available = True
        except:
            self.ml_available = False
            print("Warning: ML model not loaded, using linguistic analysis only")
    
    def predict_ml(self, text):
        """ML model prediction"""
        if not self.ml_available:
            return None
        
        try:
            # Transform text
            text_vectorized = self.tfidf.transform([text])
            
            # Get prediction
            prediction = self.ml_model.predict(text_vectorized)[0]
            probabilities = self.ml_model.predict_proba(text_vectorized)[0]
            
            fake_prob = float(probabilities[1])
            confidence = abs(fake_prob - 0.5) * 2
            
            return {
                'prediction': 'FAKE' if prediction == 1 else 'REAL',
                'probability': fake_prob,
                'confidence': confidence,
                'probabilities': {
                    'REAL': float(probabilities[0]),
                    'FAKE': float(probabilities[1])
                }
            }
        except Exception as e:
            print(f"ML prediction error: {e}")
            return None
    
    def analyze_linguistic(self, text):
        """Simple linguistic pattern analysis"""
        text_lower = text.lower()
        
        # Deceptive patterns
        deceptive_patterns = [
            'doctors dont want', 'big pharma', 'mainstream media',
            'share before deleted', 'they dont want you', 'miracle cure',
            'one weird trick', 'secret revealed', 'censored'
        ]
        deceptive_score = sum(1 for pattern in deceptive_patterns if pattern in text_lower)
        
        # Credibility markers
        credibility_patterns = [
            'study shows', 'research found', 'according to',
            'experts say', 'data shows', 'peer reviewed',
            'scientists', 'university'
        ]
        credibility_score = sum(1 for pattern in credibility_patterns if pattern in text_lower)
        
        # Calculate fake probability
        fake_prob = min((deceptive_score * 0.15) + max(0, (0.5 - credibility_score * 0.1)), 1.0)
        
        return {
            'prediction': 'FAKE' if fake_prob > 0.5 else 'REAL',
            'probability': fake_prob,
            'confidence': 0.7,
            'deceptive_score': deceptive_score,
            'credibility_score': credibility_score
        }
    
    def analyze_complete(self, text, enable_ai=True, enable_web=True):
        """
        Complete multi-layer analysis
        
        Returns comprehensive analysis from all detection methods
        """
        results = {
            'text_length': len(text),
            'word_count': len(text.split()),
            'timestamp': datetime.now().isoformat()
        }
        
        # Layer 1: ML Ensemble
        ml_result = self.predict_ml(text)
        if ml_result:
            results['ml_prediction'] = {
                'prediction': ml_result['prediction'],
                'probability': ml_result['probability'],
                'confidence': ml_result['confidence']
            }
        
        # Layer 2: Linguistic Analysis
        linguistic_result = self.analyze_linguistic(text)
        results['linguistic_analysis'] = linguistic_result
        
        # Combine predictions
        predictions = []
        confidences = []
        
        if ml_result:
            predictions.append(ml_result['probability'])
            confidences.append(ml_result['confidence'])
        
        predictions.append(linguistic_result['probability'])
        confidences.append(linguistic_result['confidence'])
        
        # Weighted average
        total_weight = sum(confidences)
        if total_weight > 0:
            final_prob = sum(p * c for p, c in zip(predictions, confidences)) / total_weight
        else:
            final_prob = sum(predictions) / len(predictions) if predictions else 0.5
        
        final_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        results['final_verdict'] = {
            'final_prediction': 'FAKE' if final_prob > 0.5 else 'REAL',
            'final_probability': final_prob,
            'final_confidence': final_confidence,
            'reliability_score': {
                'score': final_confidence * 100,
                'level': 'High' if final_confidence > 0.7 else 'Medium' if final_confidence > 0.5 else 'Low',
                'trust_recommendation': final_confidence > 0.7
            },
            'uncertainty': 1 - final_confidence,
            'disagreement': abs(predictions[0] - predictions[1]) if len(predictions) > 1 else 0
        }
        
        # Add explainability
        results['explainability'] = self.generate_explanation(results)
        
        return results
    
    def generate_explanation(self, results):
        """Generate human-readable explanation"""
        explanations = []
        
        # ML explanation
        if 'ml_prediction' in results:
            ml = results['ml_prediction']
            explanations.append({
                'source': 'Machine Learning Model',
                'verdict': ml['prediction'],
                'confidence': f"{ml['confidence']*100:.1f}%",
                'reasoning': f"ML model predicts {ml['prediction']} with {ml['probability']*100:.1f}% probability"
            })
        
        # Linguistic explanation
        ling = results['linguistic_analysis']
        explanations.append({
            'source': 'Linguistic Pattern Analysis',
            'verdict': ling['prediction'],
            'confidence': f"{ling['confidence']*100:.1f}%",
            'reasoning': f"Found {ling['deceptive_score']} deceptive patterns and {ling['credibility_score']} credibility markers"
        })
        
        # Final verdict explanation
        final = results['final_verdict']
        explanations.append({
            'source': 'FINAL VERDICT',
            'verdict': final['final_prediction'],
            'confidence': f"{final['final_confidence']*100:.1f}%",
            'reasoning': f"Reliability: {final['reliability_score']['level']} ({final['reliability_score']['score']:.1f}/100)"
        })
        
        return explanations
    
    def get_detailed_report(self, text):
        """Get comprehensive detailed report"""
        analysis = self.analyze_complete(text)
        
        report = {
            'summary': {
                'prediction': analysis['final_verdict']['final_prediction'],
                'confidence': analysis['final_verdict']['final_confidence'],
                'reliability': analysis['final_verdict']['reliability_score']['level'],
                'recommendation': 'Trust' if analysis['final_verdict']['reliability_score']['trust_recommendation'] else 'Verify Independently'
            },
            'component_analysis': {
                'machine_learning': analysis.get('ml_prediction'),
                'linguistic_patterns': analysis['linguistic_analysis']
            },
            'risk_assessment': {
                'uncertainty': analysis['final_verdict']['uncertainty'],
                'disagreement': analysis['final_verdict']['disagreement'],
                'overall_risk': 'High' if analysis['final_verdict']['final_probability'] > 0.7 else 'Medium' if analysis['final_verdict']['final_probability'] > 0.5 else 'Low'
            },
            'explanations': analysis['explainability'],
            'full_analysis': analysis
        }
        
        return report
