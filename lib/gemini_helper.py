"""
Gemini AI Helper Module
Provides functions to interact with Google's Gemini API for wage rate estimation.
"""

import os
import google.generativeai as genai
from typing import Optional


def get_wage_rate(title: str, description: str, location: str) -> Optional[float]:
	"""
	Use Gemini AI to estimate market wage rate for a volunteer task.
	
	Args:
		title: Task title
		description: Task description
		location: Task location (city)
	
	Returns:
		Estimated hourly wage rate in INR, or None if API fails
	"""
	api_key = os.getenv("GEMINI_API_KEY")
	if not api_key:
		print("Warning: GEMINI_API_KEY not found in environment variables")
		return None
	
	try:
		genai.configure(api_key=api_key)
		
		# Try available models in order of preference
		models_to_try = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro','gemini-2.5-flash']
		
		response = None
		model_used = ""
		
		for model_name in models_to_try:
			try:
				model = genai.GenerativeModel(model_name)
				prompt = f"""Estimate the market hourly wage rate in Indian Rupees (INR) for the following volunteer work:

Title: {title}
Description: {description}
Location: {location}

Consider:
- Local market rates in {location}
- Task complexity and skill requirements
- Industry standards for similar work

Respond with ONLY a numeric value (the hourly rate in INR). No currency symbols or explanations.
Example: 300"""
				
				response = model.generate_content(prompt)
				if response:
					model_used = model_name
					break
			except Exception as me:
				print(f"Model {model_name} failed: {me}")
				continue
		
		if not response:
			print("All Gemini models failed.")
			return None
			
		rate_str = response.text.strip()
		
		# Extract numeric value (handle cases like "₹300" or "300 INR")
		numeric_chars = ''.join(c for c in rate_str if c.isdigit() or c == '.')
		if numeric_chars:
			rate = float(numeric_chars)
			print(f"Succesfully estimated wage using {model_used}: ₹{rate}")
			return round(rate, 2)
		else:
			print(f"Could not extract numeric value from Gemini response ({model_used}): {rate_str}")
			return None
			
	except Exception as e:
		print(f"Gemini API error: {e}")
		return None
