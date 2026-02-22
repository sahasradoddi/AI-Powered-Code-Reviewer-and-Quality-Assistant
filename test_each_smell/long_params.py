def process_user_data(
    user_id: int, name: str, email: str, age: int, country: str, subscription_type: str
) -> dict:
    """Example function with a long parameter list, designed to trigger the 'long_parameter_list' smell in your analyzer."""
    is_adult = age >= 18
    region = "EU" if country in {"FR", "DE", "ES"} else "Other"
    
    access_level: str = (
        "FULL" if subscription_type == "premium" else
        "LIMITED" if subscription_type == "trial" else 
        "BASIC"
    )
    
    return {
        "user_id": user_id,
        "name": name,
        "email": email,
        "is_adult": is_adult,
        "region": region,
        "access_level": access_level,
    }
