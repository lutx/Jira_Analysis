from jwt import ExpiredSignatureError, InvalidTokenError

def verify_jwt_token(token):
    try:
        # ... kod weryfikacji tokena ...
        pass
    except ExpiredSignatureError:
        return None, "Token has expired"
    except InvalidTokenError:
        return None, "Invalid token"
    except Exception as e:
        return None, str(e) 