from urllib.parse import urlencode

from django.core.mail import EmailMessage
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse

from store.models import Product
from .models import Order, OrderProduct
from .forms import OrderForm
import datetime
from carts.models import Cart, CartItem
from carts.views import _cart_id


# Create your views here.
def payments(request, order_number):
    instance = Order.objects.all()
    order = Order.objects.get(is_ordered=False, order_number=order_number)
    order.is_ordered = True
    order.save()

    #Move the cart items to order product table
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_items = CartItem.objects.filter(cart=cart)
    for item in cart_items:
        order_product = OrderProduct()
        order_product.order_id = order.id
        # order_product.payment = payment
        # order_product.user_id = request.user.id
        order_product.product_id = item.product_id
        # variations=cart_item.variations,
        order_product.quantity = item.quantity
        order_product.product_price = item.product.price
        order_product.ordered = True

        order_product.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variations = cart_item.variations.all()
        order_product = OrderProduct.objects.get(id=order_product.id)
        order_product.variations.set(product_variations)
        order_product.save()




        #Reduce the quantity of the sold product
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    #Clear the cart
    CartItem.objects.filter(cart=cart).delete()


    #Send order recived email to customer
    # mail_subject = 'Thank you for your order!'
    # message = render_to_string('orders/order_received_email.html', {
    #     'user': request.user,
    #     'order': order,
    # })
    # to_email = request.user.email
    # send_email = EmailMessage(mail_subject, message, to=[to_email])
    # send_email.send()

    #Send order number and transaction id back to js function
    # base_url = reverse('order_complete')
    # query_string1 = urlencode({'order_number': order_number, 'payment_id': order.payment.payment_id})
    # url = f'{base_url}?{query_string1}'
    return redirect('store')


def place_order(request, total=0, quantity=0,):
    # current_user = request.user
    cart = Cart.objects.get(cart_id=_cart_id(request))  # get the cart using the cart id present in the session, or create it

    cart_items = CartItem.objects.filter(cart=cart)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total) / 100
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = Order()
            # data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            # data.address_line_2 = form.cleaned_data['address_line_2']
            # data.country = form.cleaned_data['country']
            # data.city = form.cleaned_data['city']
            # data.state = form.cleaned_data['state']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime('%Y%m%d')
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()
            # order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            order = Order.objects.get(is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request, 'orders/payments.html', context)
        else:
            print(form.errors)
    else:
        return redirect('checkout')


def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity

        payment = Payment.objects.get(payment_id=transID)
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment,
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')



