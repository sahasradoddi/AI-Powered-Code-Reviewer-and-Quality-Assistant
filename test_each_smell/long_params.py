def process_user_data(user_id, name, email, age, country, subscription_type):
    """
    Example function with a long parameter list, designed to trigger
    the 'long_parameter_list' smell in your analyzer.
    """
    # Simple fake logic to make it look realistic
    is_adult = age >= 18
    region = "EU" if country in {"FR", "DE", "ES"} else "Other"

    if subscription_type == "premium":
        access_level = "FULL"
    elif subscription_type == "trial":
        access_level = "LIMITED"
    else:
        access_level = "BASIC"

    return {
        "user_id": user_id,
        "name": name,
        "email": email,
        "is_adult": is_adult,
        "region": region,
        "access_level": access_level,
    }
