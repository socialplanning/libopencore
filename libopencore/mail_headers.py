from libopencore.auth import get_secret, generate_cookie_value

def build_headers(project, application, environment, object, author,
                  notification_list_address,
                  secret_filename):
    headers = [
        ("X-Opencore-Project", project),
        ("X-Opencore-Application", application),
        ("X-Opencore-Application-Environment", environment),
        ("X-Opencore-Object-Id", object),
        ("X-Opencore-Initiated-By", author),
        ("X-Opencore-Do-Not-Send-To", author),
        ("X-Opencore-Send-From", notification_list_address),
        ]
    
    _headers = sorted(headers)
    _headers = "&".join("=".join((key.lower(), val)) for key, val in _headers)

    secret = get_secret(secret_filename)
    hash = generate_cookie_value(_headers, secret)
    headers.append(("X-Opencore-Validation-Key", hash))
    return sorted(headers)

def validate_headers(headers, secret_filename):
    headers = dict((key.lower(), val) for key, val in headers.items()
                   if key.lower().startswith("x-opencore"))
    hash = headers.pop("x-opencore-validation-key")

    _headers = sorted(headers.items())
    _headers =  "&".join("=".join((key, val)) for key, val in _headers)

    secret = get_secret(secret_filename)
    if generate_cookie_value(_headers, secret) != hash:
        return False
    return True
