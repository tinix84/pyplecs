"""Small shared utilities for pyplecs.

Provides:
- dict_to_plecs_opts: coerce a dict of model vars to the PLECS optStruct
- rpc_call_wrapper: wrapper for xmlrpc.client calls with retries/backoff
- model_vars_validator: validate provided model variables against allowed set
"""
from typing import Any, Optional
import time
import socket
import xmlrpc.client


def dict_to_plecs_opts(
    varin: dict,
    coerce: bool = True,
    allowed: Optional[set] = None,
    strict: bool = False,
) -> dict:
    """Normalize a bare dict of model variables into PLECS optStruct.

    Args:
        varin: dict of name->value OR a dict already containing 'ModelVars'.
        coerce: if True, attempt to coerce numeric-looking values to float.
        allowed: optional set of allowed variable names to validate against.
        strict: if True and allowed provided, raise on unknown names.

    Returns:
        dict: {'ModelVars': {...}} with values coerced to float where possible.
    """
    if not isinstance(varin, dict):
        raise TypeError('varin must be a dict')

    if 'ModelVars' in varin:
        mv = dict(varin['ModelVars'])
    else:
        mv = dict(varin)

    # Validate names if requested
    if allowed is not None:
        filtered, _unknown = model_vars_validator(
            mv, allowed=allowed, strict=strict
        )
        mv = filtered
        mv = filtered

    normalized = {}
    for k, v in mv.items():
        if coerce:
            try:
                normalized[k] = float(v)
            except (TypeError, ValueError):
                # preserve original if it cannot be coerced
                normalized[k] = v
        else:
            normalized[k] = v

    return {'ModelVars': normalized}


def model_vars_validator(
    provided: dict, allowed: Optional[set] = None, strict: bool = False
):
    """Validate provided model vars against allowed names.

    Args:
        provided: dict of name->value
        allowed: optional set of allowed variable names
        strict: if True, raise ValueError on unknown names

    Returns:
        (filtered_dict, unknown_list)
    """
    if not isinstance(provided, dict):
        raise TypeError('provided must be a dict')

    if allowed is None:
        return dict(provided), []

    provided_names = set(provided.keys())
    unknown = list(provided_names - set(allowed))
    filtered = {k: v for k, v in provided.items() if k in allowed}

    if strict and unknown:
        raise ValueError(f'Unknown model variables: {unknown}')

    return filtered, unknown


def rpc_call_wrapper(
    proxy: Any, method_name: str, *args, retries: int = 3, backoff: float = 0.5
):
    """Call an xmlrpc method on a proxy with simple retry/backoff.

    Args:
        proxy: xmlrpc.client.ServerProxy or similar object
        method_name: dotted method name (e.g. 'plecs.simulate' or 'plecs.load')
        *args: positional args to pass to method
        retries: number of attempts on transient errors
        backoff: seconds to wait between attempts (multiplied on each retry)

    Returns:
        whatever the remote method returns

    Raises:
        The final exception if all retries fail.
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            # support dotted method names
            target = proxy
            for part in method_name.split('.'):
                target = getattr(target, part)
            return target(*args)
        except (socket.error, ConnectionRefusedError,
                xmlrpc.client.ProtocolError) as e:
            last_exc = e
            if attempt == retries:
                raise
            time.sleep(backoff * attempt)
        except xmlrpc.client.Fault:
            # remote fault is not transient; re-raise immediately
            raise

    # If we get here re-raise last exception
    if last_exc:
        raise last_exc
    raise RuntimeError('rpc_call_wrapper: unexpected failure')
