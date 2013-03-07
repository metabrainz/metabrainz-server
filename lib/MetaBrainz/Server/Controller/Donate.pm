package MetaBrainz::Server::Controller::Donate;
BEGIN { use Moose; extends 'MusicBrainz::Server::Controller'; }
use namespace::autoclean;

use Scalar::Util qw( looks_like_number );
use URI;
use LWP::UserAgent;
use DBDefs;
use JSON;

sub paypal : Local
{
    my ($self, $c) = @_;

    my $amount  = looks_like_number($c->req->params->{amount})
                    ? $c->req->params->{amount} : undef;
    my $recur  = looks_like_number($c->req->params->{recur})
                    ? $c->req->params->{recur} : undef;

    $c->stash(
        amount => $amount,
        recur => $recur,
    );
}

sub wepay : Local
{
    my ($self, $c) = @_;

    my $amount  = looks_like_number($c->req->params->{amount})
                    ? $c->req->params->{amount} : 10;
    my $recur  = looks_like_number($c->req->params->{recur})
                    ? $c->req->params->{recur} : 0;

    $c->stash(
        recur => $recur
    );

    my $form = $c->form(
        form => 'WePay',
        init_object => {amount => $amount,
                        recur => $recur}
    );

    if ($c->form_posted && $form->submitted_and_valid($c->req->params)) {
        my $ua = LWP::UserAgent->new(agent => 'metabrainz-server');
        my $type = $form->field('recur')->value ? 'preapproval' : 'checkout';

        my $editor = $form->field('editor')->value || 'NONE';
        my $anonymous = $form->field('anonymous')->value // '0';
        my $can_contact = $form->field('can_contact')->value // '0';

        my $url = 'https://wepayapi.com/v2/';
        if (DBDefs::WEPAY_USE_STAGING) {
            $url = 'https://stage.wepayapi.com/v2/';
        }
        my $content = {
            account_id => DBDefs::WEPAY_ACCOUNT_ID,
            amount => $form->field('amount')->value,
            mode => 'regular',
            redirect_uri => $c->uri_for_action('/donate/complete'),
            require_shipping => 1
        };
        if ($form->field('recur')->value) {
            $content->{period} = 'monthly';
            $content->{auto_recur} = 'true';
            $content->{short_description} = 'Recurring donation to MetaBrainz Foundation';
        } else {
            $content->{type} = 'DONATION';
            $content->{short_description} = 'Donation to MetaBrainz Foundation';
        }
        if ($c->uri_for_action('/donate/wepay_ipn', [$editor, $anonymous, $can_contact]) !~ /localhost/) {
            $content->{callback_uri} = $c->uri_for_action('/donate/wepay_ipn', [$editor, $anonymous, $can_contact]);
        }
        my $checkout = $ua->post($url . '/' . $type . '/create',
                                 'Authorization' => 'Bearer ' . DBDefs::WEPAY_ACCESS_TOKEN,
                                 Content => $content);
        my $data = JSON->new->utf8->decode($checkout->content);

        if ($data->{error}) {
            $c->res->redirect($c->uri_for_action('/donate/error', { 'message' => $data->{error_description} }));
        } else {
            $c->res->redirect($data->{$type . '_uri'});
            $c->detach;
        }
    }
}

sub complete : Local { }
sub cancelled : Local { }
sub error : Local {
    my ($self, $c) = @_;
    if ($c->req->query_params->{message}) {
       $c->stash->{message} = $c->req->query_params->{message};
    }
}

sub paypal_ipn : Path('paypal-ipn') {
    my ($self, $c) = @_;

    my $encoder = URI->new;
    $encoder->query_form(
        [ map { $_, $c->req->params->{$_} }
              @{ $c->req->_body->param_order }
        ]
    );

    if (!$c->model('Donation')->verify_paypal_transaction($encoder->query)) {
        $c->res->status(403);
        $c->detach;
    }

    $c->model('Donation')->try_log_paypal_donation($c->req->params);
    $c->res->body('');
    $c->res->status(200);
    $c->detach;
}

sub wepay_ipn : Path('wepay-ipn') Args(3) {
    my ($self, $c, $editor, $anonymous, $can_email) = @_;

    my $res = 1;
    if ($c->req->params->{checkout_id}) {
        my $checkout_id = $c->req->params->{checkout_id};
        $editor = "" if $editor eq 'NONE';
        $res = $c->model('Donation')->verify_and_log_wepay_checkout($checkout_id,
                                                                    $editor,
                                                                    $anonymous,
                                                                    $can_email);
    }

    unless ($res) {
        $c->res->status(500);
        $c->detach;
    }

    $c->res->body('');
    $c->res->status(200);
    $c->detach;
}

sub index : Path Args(0)
{
    my ($self, $c) = @_;
}

sub add : Path('/admin/add-donation') {
    my ($self, $c) = @_;

    $c->authenticate({ realm => "metabrainz" });

    my $form = $c->form(form => 'Donation');
    if ($c->form_posted && $form->submitted_and_valid($c->req->params)) {
        $c->model('Donation')->manually_add($form->value);
        $c->res->redirect(
            $c->uri_for_action('/donations/by_date'));
    }
}

1;
