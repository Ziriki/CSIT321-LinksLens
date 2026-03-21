def get_fullname(user_account, default="N/A"):
    """Extract FullName from a UserAccount's related UserDetails safely."""
    if user_account and user_account.details:
        return user_account.details.FullName
    return default
