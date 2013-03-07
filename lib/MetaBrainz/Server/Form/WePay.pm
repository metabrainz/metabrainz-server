package MetaBrainz::Server::Form::WePay;
use Moose;
use HTML::FormHandler::Moose;

extends 'MusicBrainz::Server::Form';

has '+name' => ( default => 'donation' );

has_field can_contact => (
    type => 'Boolean'
);

has_field anonymous => (
    type => 'Boolean'
);

has_field recur => (
    type => 'Boolean'
);

has_field amount => (
    type => 'Money',
    required => 1
);

has_field editor => (
    type => '+MusicBrainz::Server::Form::Field::Text'
);

1;
