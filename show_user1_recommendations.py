#!/usr/bin/env python3
"""Display recommendations for user_0001"""

from spendsense.recommend.engine import generate_recommendations
from spendsense.ingest.database import get_session

session = get_session()
try:
    recommendations = generate_recommendations('user_0001', session=session, max_education=5, max_offers=3)
    
    print('='*80)
    print(f'RECOMMENDATIONS FOR USER: user_0001')
    print('='*80)
    print(f'Total Recommendations: {len(recommendations)}')
    if recommendations:
        print(f'Persona: {recommendations[0].persona}')
    print()
    
    education_count = sum(1 for r in recommendations if r.recommendation_type == 'education')
    offer_count = sum(1 for r in recommendations if r.recommendation_type == 'offer')
    
    print(f'📚 Education Recommendations: {education_count}')
    print(f'💼 Partner Offers: {offer_count}')
    print()
    print('='*80)
    print()
    
    edu_num = 1
    offer_num = 1
    
    for rec in recommendations:
        if rec.recommendation_type == 'education':
            print(f'📚 EDUCATION #{edu_num}')
            print(f'   Template ID: {rec.template_id}')
            print(f'   Content:')
            print(f'   {rec.content}')
            print()
            print(f'   Rationale:')
            print(f'   {rec.rationale}')
            print()
            print('-'*80)
            print()
            edu_num += 1
        else:
            print(f'💼 PARTNER OFFER #{offer_num}')
            print(f'   Offer ID: {rec.offer_id}')
            print(f'   Description:')
            print(f'   {rec.content}')
            print()
            print(f'   Rationale:')
            print(f'   {rec.rationale}')
            print()
            print('-'*80)
            print()
            offer_num += 1
    
finally:
    session.close()

