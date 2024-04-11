from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

class CreateStrategyForm(FlaskForm):
    uid = StringField('Unique ID', validators=[DataRequired(), Length(min=2, max=64)])
    strategy_name = StringField('Strategy Name', validators=[DataRequired(), Length(min=2, max=255)])
    coin_pair = StringField('Coin Pair', validators=[DataRequired(), Length(max=20)])
    time_frame = StringField('Time Frame', validators=[DataRequired(), Length(max=10)])
    description = TextAreaField('Description')
    submit = SubmitField('Create Strategy')

class UpdateStrategyForm(FlaskForm):
    strategy_name = StringField('Strategy Name', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description')
    coin_pair = StringField('Coin Pair', validators=[DataRequired(), Length(max=20)])
    time_frame = StringField('Time Frame', validators=[DataRequired(), Length(max=10)])
    submit = SubmitField('Update Strategy')